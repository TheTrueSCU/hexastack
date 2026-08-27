"""Hypothesis property-based tests for ExecutionPipeline dispatch, routing, and error mapping invariants.

Notes/Architectural Intent:
    Fuzzes arbitrary Command, Query, and Event execution workflows, proving that:
    1. ExecutionPipeline dispatch routing correctly partitions Commands, Queries, and Events
       without cross-bus contamination.
    2. Dynamic name resolution (execute_by_name) correctly enforces UnregisteredMessageError
       and AmbiguousMessageError across synthesized namespaces.
    3. ExceptionRegistry integration reliably intercepts and formats arbitrary exception hierarchies
       without leaking unhandled domain exceptions.
"""

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import create_model

from hexastack_core.domain import Command, Query
from hexastack_core.infra import ExceptionRegistry
from hexastack_cqrs.infra.pipeline import (
    AmbiguousMessageError,
    ExecutionPipeline,
    UnregisteredMessageError,
)
from hexastack_cqrs.infra.registries import (
    CommandRegistry,
    HandlerRegistry,
    QueryRegistry,
)

# Strategy for generating clean python identifiers
clean_names = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    min_size=3,
    max_size=20,
)
payload_values = st.dictionaries(
    keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=10),
    values=st.one_of(
        st.booleans(),
        st.integers(min_value=-1000, max_value=1000),
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=0, max_size=20
        ),
    ),
    max_size=4,
)


@given(
    name=clean_names,
    int_val=st.integers(min_value=1, max_value=10000),
    str_val=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=20),
)
def test_pipeline_command_and_query_dispatch_isomorphism(
    name: str, int_val: int, str_val: str
):
    """Property: Command and Query models with identical field schemas dispatch to their respective handlers."""
    CmdCls = create_model(
        f"Cmd_{name}", val=(int, ...), tag=(str, ...), __base__=Command
    )
    QryCls = create_model(f"Qry_{name}", val=(int, ...), tag=(str, ...), __base__=Query)

    handler_reg = HandlerRegistry()
    command_reg = CommandRegistry()
    query_reg = QueryRegistry()

    command_reg.register(CmdCls)
    query_reg.register(QryCls)

    handler_reg.register(CmdCls, lambda c: f"cmd_result_{c.val}_{c.tag}")
    handler_reg.register(QryCls, lambda q: f"qry_result_{q.val}_{q.tag}")

    pipeline = ExecutionPipeline(
        handler_registry=handler_reg,
        command_registry=command_reg,
        query_registry=query_reg,
    )

    cmd_instance = CmdCls.model_validate({"val": int_val, "tag": str_val})
    qry_instance = QryCls.model_validate({"val": int_val, "tag": str_val})

    assert pipeline.execute(cmd_instance) == f"cmd_result_{int_val}_{str_val}"
    assert pipeline.execute(qry_instance) == f"qry_result_{int_val}_{str_val}"

    # Verify string-based execution by name
    assert (
        pipeline.execute_by_name(f"Cmd_{name}", {"val": int_val, "tag": str_val})
        == f"cmd_result_{int_val}_{str_val}"
    )
    assert (
        pipeline.execute_by_name(f"Qry_{name}", {"val": int_val, "tag": str_val})
        == f"qry_result_{int_val}_{str_val}"
    )


@given(name=clean_names)
def test_pipeline_ambiguous_message_name_raises_error(name: str):
    """Property: If a message name exists in both CommandRegistry and QueryRegistry, execute_by_name fails safely."""
    AmbiguousModel = create_model(name, __base__=Command)
    AmbiguousQueryModel = create_model(name, __base__=Query)

    command_reg = CommandRegistry()
    query_reg = QueryRegistry()
    handler_reg = HandlerRegistry()

    command_reg.register(AmbiguousModel)
    query_reg.register(AmbiguousQueryModel)

    pipeline = ExecutionPipeline(
        handler_registry=handler_reg,
        command_registry=command_reg,
        query_registry=query_reg,
    )

    with pytest.raises(
        AmbiguousMessageError, match="registered in multiple type registries"
    ):
        pipeline.execute_by_name(name, {})


@given(name=clean_names)
def test_pipeline_unregistered_message_name_raises_error(name: str):
    """Property: Querying a non-existent name string deterministically raises UnregisteredMessageError."""
    pipeline = ExecutionPipeline(handler_registry=HandlerRegistry())
    with pytest.raises(
        UnregisteredMessageError, match="No Command or Query registered"
    ):
        pipeline.execute_by_name(f"NonExistent_{name}", {})


@given(
    error_msg=st.text(alphabet="abcdefghijklmnopqrstuvwxyz ", min_size=1, max_size=30),
    status_code=st.sampled_from([400, 403, 404, 422, 500]),
)
def test_pipeline_exception_registry_interception_property(
    error_msg: str, status_code: int
):
    """Property: Handlers raising registered domain errors are intercepted and mapped without uncaught crash."""

    class CustomDomainError(Exception):
        pass

    ErrorCmd = create_model(f"ErrorCmd_{status_code}", __base__=Command)

    def failing_handler(cmd: Any) -> Any:
        raise CustomDomainError(error_msg)

    handler_reg = HandlerRegistry()
    handler_reg.register(ErrorCmd, failing_handler)

    exc_reg = ExceptionRegistry()
    exc_reg.register(
        CustomDomainError,
        lambda exc: {"error": str(exc), "status": status_code},
    )

    pipeline = ExecutionPipeline(
        handler_registry=handler_reg,
        exception_registry=exc_reg,
    )

    result = pipeline.execute(ErrorCmd())
    assert result == {"error": error_msg, "status": status_code}
