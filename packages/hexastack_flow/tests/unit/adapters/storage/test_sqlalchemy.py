"""Unit tests for SqlAlchemyWorkflowStore adapter.

Notes/Architectural Intent:
    Tests persistence, retrieval, listing, and deletion of workflow runs
    and step checkpoints using an in-memory SQLite SQLAlchemy engine.
"""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from hexaflow.domain.state import (
    CheckpointRecord,
    StepStatus,
    WorkflowExecutionState,
    WorkflowStatus,
)
from sqlalchemy import create_engine

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_flow.adapters.storage.sqlalchemy import SqlAlchemyWorkflowStore


@pytest.fixture
def sqlite_store() -> SqlAlchemyWorkflowStore:
    """Fixture providing an initialized SqlAlchemyWorkflowStore on in-memory SQLite."""
    engine = create_engine("sqlite:///:memory:")
    store = SqlAlchemyWorkflowStore(engine)
    store.create_tables()
    return store


def test_save_and_get_workflow_run(sqlite_store: SqlAlchemyWorkflowStore) -> None:
    """Validate saving and retrieving a WorkflowExecutionState."""
    now = datetime.now(UTC)
    state = WorkflowExecutionState(
        run_id="run-sqlite-1",
        workflow_name="test_sqlite_wf",
        status=WorkflowStatus.RUNNING,
        started_at=now,
        finished_at=None,
        current_stage="stage_1",
    )

    sqlite_store.save_run(state)
    retrieved = sqlite_store.get_run("run-sqlite-1")

    assert retrieved is not None
    run_id = retrieved.run_id
    wf_name = retrieved.workflow_name
    status = retrieved.status
    stage = retrieved.current_stage

    assert run_id == "run-sqlite-1"
    assert wf_name == "test_sqlite_wf"
    assert status == WorkflowStatus.RUNNING
    assert stage == "stage_1"


def test_update_workflow_run(sqlite_store: SqlAlchemyWorkflowStore) -> None:
    """Validate upsert/update of existing WorkflowExecutionState."""
    now = datetime.now(UTC)
    state = WorkflowExecutionState(
        run_id="run-update-1",
        workflow_name="updatable",
        status=WorkflowStatus.RUNNING,
        started_at=now,
        finished_at=None,
    )
    sqlite_store.save_run(state)

    # Update status to COMPLETED
    updated_state = WorkflowExecutionState(
        run_id="run-update-1",
        workflow_name="updatable",
        status=WorkflowStatus.COMPLETED,
        started_at=now,
        finished_at=datetime.now(UTC),
    )
    sqlite_store.save_run(updated_state)

    retrieved = sqlite_store.get_run("run-update-1")
    assert retrieved is not None
    assert retrieved.status == WorkflowStatus.COMPLETED


def test_get_nonexistent_run_returns_none(
    sqlite_store: SqlAlchemyWorkflowStore,
) -> None:
    """Validate retrieving unknown run ID returns None."""
    retrieved = sqlite_store.get_run("nonexistent-run")
    assert retrieved is None


def test_list_workflow_runs(sqlite_store: SqlAlchemyWorkflowStore) -> None:
    """Validate listing runs with limit and offset."""
    now = datetime.now(UTC)
    for i in range(5):
        st = WorkflowExecutionState(
            run_id=f"run-{i}",
            workflow_name=f"wf-{i}",
            status=WorkflowStatus.COMPLETED,
            started_at=now,
            finished_at=now,
        )
        sqlite_store.save_run(st)

    runs = sqlite_store.list_runs(limit=3, offset=0)
    assert len(runs) == 3


def test_step_checkpoint_crud(sqlite_store: SqlAlchemyWorkflowStore) -> None:
    """Validate save, get, list, and delete of step checkpoints."""
    now = datetime.now(UTC)

    # Create run first
    st = WorkflowExecutionState(
        run_id="run-chk-1",
        workflow_name="chk_wf",
        status=WorkflowStatus.RUNNING,
        started_at=now,
        finished_at=None,
    )
    sqlite_store.save_run(st)

    chk = CheckpointRecord(
        checkpoint_id="chk-1",
        run_id="run-chk-1",
        stage_name="stage_a",
        step_name="step_a",
        status=StepStatus.COMPLETED,
        attempt_number=1,
        input_payload={"param": 42},
        output_payload={"result": "ok"},
        error_traceback=None,
        started_at=now,
        completed_at=now,
    )

    sqlite_store.save_checkpoint(chk)

    # Get
    retrieved_chk = sqlite_store.get_checkpoint("run-chk-1", "step_a")
    assert retrieved_chk is not None
    assert retrieved_chk.status == StepStatus.COMPLETED
    assert retrieved_chk.output_payload == {"result": "ok"}

    # Update
    updated_chk = CheckpointRecord(
        checkpoint_id="chk-1",
        run_id="run-chk-1",
        stage_name="stage_a",
        step_name="step_a",
        status=StepStatus.COMPLETED,
        attempt_number=2,
        input_payload={"param": 42},
        output_payload={"result": "ok_updated"},
        error_traceback=None,
        started_at=now,
        completed_at=now,
    )
    sqlite_store.save_checkpoint(updated_chk)
    retrieved_updated = sqlite_store.get_checkpoint("run-chk-1", "step_a")
    assert retrieved_updated is not None
    assert retrieved_updated.output_payload == {"result": "ok_updated"}

    # Nonexistent checkpoint
    none_chk = sqlite_store.get_checkpoint("run-chk-1", "nonexistent")
    assert none_chk is None

    # List
    chk_list = sqlite_store.get_checkpoints("run-chk-1")
    assert len(chk_list) == 1

    # Delete
    sqlite_store.delete_checkpoints("run-chk-1")
    after_del = sqlite_store.get_checkpoints("run-chk-1")
    assert len(after_del) == 0


def test_missing_sqlalchemy_dependency() -> None:
    """Ensure MissingDependencyError is raised when sqlalchemy is not installed."""
    with (
        patch(
            "hexastack_flow.adapters.storage.sqlalchemy.importlib.util.find_spec",
            return_value=None,
        ),
        pytest.raises(MissingDependencyError, match="sqlalchemy is required"),
    ):
        SqlAlchemyWorkflowStore(None)
