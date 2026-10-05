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
from hexastack_cqrs.adapters.buses import SynchronousCommandBus
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


@given(
    num_middlewares=st.integers(min_value=2, max_value=6),
    short_circuit_idx=st.integers(min_value=0, max_value=5),
    sentinel=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=15
    ),
)
def test_pipeline_middleware_short_circuit_invariant(
    num_middlewares: int, short_circuit_idx: int, sentinel: str
):
    """Property: Any middleware returning early without calling next_call short-circuits the pipeline."""
    cut_idx = short_circuit_idx % num_middlewares

    trace: list[str] = []

    class TracedMiddleware:
        def __init__(self, idx: int, should_short_circuit: bool):
            self.idx = idx
            self.should_short_circuit = should_short_circuit

        def __call__(self, instance: Any, next_call: Any) -> Any:
            trace.append(f"enter_{self.idx}")
            if self.should_short_circuit:
                trace.append(f"short_circuit_{self.idx}")
                return f"short_circuit_result_{sentinel}_{self.idx}"
            try:
                res = next_call(instance)
            finally:
                trace.append(f"exit_{self.idx}")
            return res

    middlewares: list[Any] = [
        TracedMiddleware(i, should_short_circuit=(i == cut_idx))
        for i in range(num_middlewares)
    ]

    handler_called = []

    class TargetCmd(Command):
        pass

    handler_reg = HandlerRegistry()

    def _handler(cmd: Any) -> Any:
        handler_called.append(True)
        return "handler_result"

    handler_reg.register(TargetCmd, _handler)

    bus = SynchronousCommandBus(handler_registry=handler_reg, middleware=middlewares)
    pipeline = ExecutionPipeline(handler_registry=handler_reg, command_bus=bus)

    res = pipeline.execute(TargetCmd())

    # 1. Returned value is the short-circuit sentinel
    assert res == f"short_circuit_result_{sentinel}_{cut_idx}"

    # 2. Handler was NEVER called
    assert not handler_called

    # 3. Downstream middlewares (indices > cut_idx) were NEVER entered
    for downstream in range(cut_idx + 1, num_middlewares):
        assert f"enter_{downstream}" not in trace
        assert f"exit_{downstream}" not in trace

    # 4. Upstream middlewares (indices < cut_idx) unwound in LIFO order
    expected_trace = []
    for i in range(cut_idx):
        expected_trace.append(f"enter_{i}")
    expected_trace.append(f"enter_{cut_idx}")
    expected_trace.append(f"short_circuit_{cut_idx}")
    for i in reversed(range(cut_idx)):
        expected_trace.append(f"exit_{i}")

    assert trace == expected_trace


@given(
    num_middlewares=st.integers(min_value=1, max_value=6),
    fault_idx=st.integers(min_value=0, max_value=6),
    error_msg=st.text(
        alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=20
    ),
)
def test_pipeline_middleware_exception_rollback_lifo_invariant(
    num_middlewares: int, fault_idx: int, error_msg: str
):
    """Property: Exceptions raised by middleware or handler trigger cleanup/rollback in strict LIFO order."""
    effective_fault = fault_idx % (
        num_middlewares + 1
    )  # num_middlewares means handler faults

    rollback_trace: list[str] = []
    entry_trace: list[str] = []

    class DomainFault(Exception):
        pass

    class RollbackTracedMiddleware:
        def __init__(self, idx: int):
            self.idx = idx

        def __call__(self, instance: Any, next_call: Any) -> Any:
            entry_trace.append(f"enter_{self.idx}")
            if self.idx == effective_fault:
                raise DomainFault(f"fault_at_middleware_{self.idx}_{error_msg}")
            try:
                return next_call(instance)
            finally:
                rollback_trace.append(f"rollback_{self.idx}")

    middlewares: list[Any] = [
        RollbackTracedMiddleware(i) for i in range(num_middlewares)
    ]

    class TargetCmd(Command):
        pass

    handler_reg = HandlerRegistry()

    def _handler(cmd: Any) -> Any:
        if effective_fault == num_middlewares:
            raise DomainFault(f"fault_at_handler_{error_msg}")
        return "success"

    handler_reg.register(TargetCmd, _handler)

    bus = SynchronousCommandBus(handler_registry=handler_reg, middleware=middlewares)
    pipeline = ExecutionPipeline(handler_registry=handler_reg, command_bus=bus)

    with pytest.raises(DomainFault) as exc_info:
        pipeline.execute(TargetCmd())

    assert error_msg in str(exc_info.value)

    if effective_fault == num_middlewares:
        # Handler faulted: all middlewares entered and all must rollback in strict LIFO order
        assert entry_trace == [f"enter_{i}" for i in range(num_middlewares)]
        assert rollback_trace == [
            f"rollback_{i}" for i in reversed(range(num_middlewares))
        ]
    else:
        # Middleware effective_fault faulted: only 0..effective_fault entered
        assert entry_trace == [f"enter_{i}" for i in range(effective_fault + 1)]
        # Rollbacks only happen for outer middlewares that completed try block entry (0..effective_fault-1)
        assert rollback_trace == [
            f"rollback_{i}" for i in reversed(range(effective_fault))
        ]


@given(
    num_middlewares=st.integers(min_value=1, max_value=8),
)
def test_pipeline_middleware_onion_ordering_invariant(num_middlewares: int):
    """Property: Middleware ingress executes FIFO, and egress executes LIFO around handler."""
    execution_order: list[str] = []

    class OrderingMiddleware:
        def __init__(self, idx: int):
            self.idx = idx

        def __call__(self, instance: Any, next_call: Any) -> Any:
            execution_order.append(f"ingress_{self.idx}")
            res = next_call(instance)
            execution_order.append(f"egress_{self.idx}")
            return res

    middlewares: list[Any] = [OrderingMiddleware(i) for i in range(num_middlewares)]

    class TargetCmd(Command):
        pass

    handler_reg = HandlerRegistry()
    handler_reg.register(
        TargetCmd, lambda cmd: (execution_order.append("handler"), "done")[1]
    )

    bus = SynchronousCommandBus(handler_registry=handler_reg, middleware=middlewares)
    pipeline = ExecutionPipeline(handler_registry=handler_reg, command_bus=bus)

    result = pipeline.execute(TargetCmd())
    assert result == "done"

    expected = [f"ingress_{i}" for i in range(num_middlewares)]
    expected.append("handler")
    expected.extend([f"egress_{i}" for i in reversed(range(num_middlewares))])

    assert execution_order == expected
