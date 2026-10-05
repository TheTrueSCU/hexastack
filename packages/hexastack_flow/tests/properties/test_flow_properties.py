"""Property-based tests for hexastack-flow domain models and CQRS step adapters.

Notes/Architectural Intent:
    Verifies invariants of CQRS command/query step construction, metadata attachment,
    and workflow execution result serialization using Hypothesis.
"""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

from hexaflow.domain.models import StepDefinition
from hexaflow.domain.state import StepContext
from hypothesis import given, settings
from hypothesis import strategies as st

from hexastack_core.domain import Command, Query
from hexastack_cqrs.ports.buses import CommandBusPort, QueryBusPort
from hexastack_flow.adapters.cqrs.steps import as_command_step, as_query_step
from hexastack_flow.domain.models import CqrsStepMetadata, WorkflowExecutionResult


class DummyCommand(Command):
    """Stub command for property testing."""

    payload: str


class DummyQuery(Query[str]):
    """Stub query for property testing."""

    query_param: str


st_step_name = st.from_regex(r"[a-z][a-z0-9_]{2,20}", fullmatch=True)
st_description = st.text(max_size=60)
st_timeout = st.one_of(
    st.none(), st.floats(min_value=0.1, max_value=3600.0, allow_nan=False)
)
st_deps = st.lists(st.from_regex(r"dep_[a-z0-9]{2,8}", fullmatch=True), max_size=4).map(
    tuple
)


@given(
    name=st_step_name,
    description=st_description,
    timeout=st_timeout,
    depends_on=st_deps,
)
@settings(max_examples=40)
def test_as_command_step_constructs_valid_step_definition(
    name: str,
    description: str,
    timeout: float | None,
    depends_on: tuple[str, ...],
) -> None:
    """Property test verifying as_command_step preserves all metadata and parameters.

    Args:
        name: Generated step name.
        description: Generated step description.
        timeout: Optional timeout in seconds.
        depends_on: Tuple of prerequisite step names.

    Notes/Architectural Intent:
        Asserts that CQRS command step factories produce fully conforming hexaflow
        StepDefinition objects with valid embedded CqrsStepMetadata.
    """
    mock_bus = MagicMock(spec=CommandBusPort)

    def factory(ctx: StepContext) -> Command:
        return DummyCommand(payload="test")

    step_def = as_command_step(
        name=name,
        command_factory=factory,
        command_bus=mock_bus,
        depends_on=depends_on,
        description=description,
        timeout_seconds=timeout,
    )

    assert isinstance(step_def, StepDefinition)
    assert step_def.name == name
    assert step_def.depends_on == depends_on
    assert step_def.timeout_seconds == timeout

    # Verify embedded CQRS metadata
    assert "cqrs" in step_def.metadata
    meta = CqrsStepMetadata.model_validate(step_def.metadata["cqrs"])
    assert meta.step_type == "command"
    assert meta.message_type == name
    assert meta.description == description
    assert meta.requires_transaction is True


@given(
    name=st_step_name,
    description=st_description,
    timeout=st_timeout,
    depends_on=st_deps,
)
@settings(max_examples=40)
def test_as_query_step_constructs_valid_step_definition(
    name: str,
    description: str,
    timeout: float | None,
    depends_on: tuple[str, ...],
) -> None:
    """Property test verifying as_query_step preserves all metadata and parameters.

    Args:
        name: Generated step name.
        description: Generated step description.
        timeout: Optional timeout in seconds.
        depends_on: Tuple of prerequisite step names.

    Notes/Architectural Intent:
        Asserts that CQRS query step factories produce hexaflow StepDefinition objects
        flagged with requires_transaction=False.
    """
    mock_bus = MagicMock(spec=QueryBusPort)

    def factory(ctx: StepContext) -> Query[str]:
        return DummyQuery(query_param="query")

    step_def = as_query_step(
        name=name,
        query_factory=factory,
        query_bus=mock_bus,
        depends_on=depends_on,
        description=description,
        timeout_seconds=timeout,
    )

    assert isinstance(step_def, StepDefinition)
    assert step_def.name == name
    assert step_def.depends_on == depends_on
    assert step_def.timeout_seconds == timeout

    assert "cqrs" in step_def.metadata
    meta = CqrsStepMetadata.model_validate(step_def.metadata["cqrs"])
    assert meta.step_type == "query"
    assert meta.message_type == name
    assert meta.description == description
    assert meta.requires_transaction is False


@given(
    run_id=st.from_regex(r"run_[a-z0-9]{4,12}", fullmatch=True),
    workflow_name=st.from_regex(r"wf_[a-z0-9]{3,10}", fullmatch=True),
    status=st.sampled_from(["COMPLETED", "SUSPENDED", "ABORTED", "FAILED"]),
    completed=st.lists(
        st.from_regex(r"step_[a-z0-9]{2,6}", fullmatch=True), max_size=5
    ).map(tuple),
    failed=st.lists(
        st.from_regex(r"fail_[a-z0-9]{2,6}", fullmatch=True), max_size=3
    ).map(tuple),
    outputs=st.dictionaries(
        keys=st.from_regex(r"out_[a-z0-9]{2,6}", fullmatch=True),
        values=st.one_of(st.integers(-100, 100), st.text(max_size=20), st.booleans()),
        max_size=4,
    ),
    error_summary=st.one_of(st.none(), st.text(max_size=50)),
)
@settings(max_examples=40)
def test_workflow_execution_result_serialization_roundtrip(
    run_id: str,
    workflow_name: str,
    status: str,
    completed: tuple[str, ...],
    failed: tuple[str, ...],
    outputs: dict[str, Any],
    error_summary: str | None,
) -> None:
    """Property test verifying lossless JSON serialization of WorkflowExecutionResult.

    Args:
        run_id: Unique run ID.
        workflow_name: Workflow name.
        status: Status string.
        completed: Tuple of completed step names.
        failed: Tuple of failed step names.
        outputs: Output dictionary.
        error_summary: Optional error message.

    Notes/Architectural Intent:
        Guarantees that WorkflowExecutionResult serializes and deserializes
        identically across Pydantic models.
    """
    now = datetime.now(UTC)
    result = WorkflowExecutionResult(
        run_id=run_id,
        workflow_name=workflow_name,
        status=status,
        completed_steps=completed,
        failed_steps=failed,
        outputs=outputs,
        started_at=now,
        ended_at=now,
        error_summary=error_summary,
    )

    json_data = result.model_dump_json()
    restored = WorkflowExecutionResult.model_validate_json(json_data)

    assert restored == result
    assert restored.run_id == run_id
    assert restored.workflow_name == workflow_name
    assert restored.status == status
    assert restored.completed_steps == completed
    assert restored.failed_steps == failed
    assert restored.outputs == outputs
    assert restored.error_summary == error_summary
