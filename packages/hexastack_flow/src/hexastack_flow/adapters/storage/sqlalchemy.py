"""SQLAlchemy workflow state store adapter implementing WorkflowStateStorePort.

Notes/Architectural Intent:
    Persists workflow execution states and step checkpoints into relational databases
    (PostgreSQL, MySQL, SQLite) using SQLAlchemy. Enables workflows to participate in
    enterprise database transactions alongside domain entities.
"""

import importlib.util
import json
from datetime import UTC
from typing import Any

from hexaflow.domain.state import (
    CheckpointRecord,
    StepStatus,
    WorkflowExecutionState,
    WorkflowStatus,
)
from hexaflow.ports.storage import WorkflowStateStorePort

from hexastack_core.domain.exceptions import MissingDependencyError

__all__ = [
    "SqlAlchemyWorkflowStore",
]


class SqlAlchemyWorkflowStore(WorkflowStateStorePort):
    """Workflow state store adapter backed by SQLAlchemy tables.

    Notes/Architectural Intent:
        Implements WorkflowStateStorePort using SQLAlchemy Core tables,
        allowing clean persistence across arbitrary relational DB engines
        without coupling to ORM base hierarchies.
    """

    def __init__(self, engine_or_session: Any) -> None:
        """Initialize SQLAlchemy workflow state store.

        Args:
            engine_or_session: An active SQLAlchemy Engine, Connection, or Session instance.

        Raises:
            MissingDependencyError: If sqlalchemy is not installed.
        """
        if importlib.util.find_spec("sqlalchemy") is None:
            raise MissingDependencyError(
                "sqlalchemy is required to use SqlAlchemyWorkflowStore. "
                "Install via 'pip install hexastack-flow[db]'."
            )

        from sqlalchemy import (
            Column,
            DateTime,
            Integer,
            MetaData,
            String,
            Table,
            Text,
            UniqueConstraint,
        )

        self._target = engine_or_session
        self._metadata = MetaData()

        self._workflow_runs = Table(
            "hexaflow_workflow_runs",
            self._metadata,
            Column("run_id", String(128), primary_key=True),
            Column("workflow_name", String(256), nullable=False),
            Column("status", String(32), nullable=False),
            Column("started_at", DateTime(timezone=True), nullable=False),
            Column("finished_at", DateTime(timezone=True), nullable=True),
            Column("current_stage", String(128), nullable=True),
            Column("error_summary", Text, nullable=True),
        )

        self._step_checkpoints = Table(
            "hexaflow_step_checkpoints",
            self._metadata,
            Column("checkpoint_id", String(128), primary_key=True),
            Column("run_id", String(128), nullable=False),
            Column("stage_name", String(128), nullable=False),
            Column("step_name", String(128), nullable=False),
            Column("status", String(32), nullable=False),
            Column("attempt_number", Integer, nullable=False),
            Column("input_payload", Text, nullable=True),
            Column("output_payload", Text, nullable=True),
            Column("error_traceback", Text, nullable=True),
            Column("started_at", DateTime(timezone=True), nullable=False),
            Column("completed_at", DateTime(timezone=True), nullable=True),
            UniqueConstraint("run_id", "step_name", name="uq_step_checkpoint"),
        )

    def create_tables(self) -> None:
        """Create underlying workflow run and checkpoint tables if they do not exist.

        Notes/Architectural Intent:
            Convenience helper for embedded or development workflows.
            In production, schema migrations should manage table lifecycles.
        """
        from sqlalchemy import Engine

        if isinstance(self._target, Engine):
            self._metadata.create_all(self._target)
        elif hasattr(self._target, "bind") and self._target.bind is not None:
            self._metadata.create_all(self._target.bind)

    def _execute(self, statement: Any, parameters: dict[str, Any] | None = None) -> Any:
        """Execute a SQL statement against the underlying engine or session.

        Args:
            statement: SQLAlchemy executable statement.
            parameters: Optional query parameter bindings.

        Returns:
            Execution cursor or result proxy.
        """
        from sqlalchemy import Engine
        from sqlalchemy.orm import Session

        if isinstance(self._target, Session):
            result = self._target.execute(statement, parameters or {})
            self._target.flush()
            return result
        if isinstance(self._target, Engine):
            with self._target.begin() as conn:
                return conn.execute(statement, parameters or {})
        else:
            return self._target.execute(statement, parameters or {})

    def save_run(self, state: WorkflowExecutionState) -> None:
        """Persist or update aggregate workflow execution run state.

        Args:
            state: The current WorkflowExecutionState to persist.
        """
        from sqlalchemy import select

        check_stmt = select(self._workflow_runs.c.run_id).where(
            self._workflow_runs.c.run_id == state.run_id
        )
        existing = self._execute(check_stmt).scalar_one_or_none()

        values = {
            "workflow_name": state.workflow_name,
            "status": state.status.value,
            "started_at": state.started_at,
            "finished_at": state.finished_at,
            "current_stage": state.current_stage,
            "error_summary": state.error_summary,
        }

        if existing is not None:
            update_stmt = (
                self._workflow_runs.update()
                .where(self._workflow_runs.c.run_id == state.run_id)
                .values(**values)
            )
            self._execute(update_stmt)
        else:
            values["run_id"] = state.run_id
            insert_stmt = self._workflow_runs.insert().values(**values)
            self._execute(insert_stmt)

    def get_run(self, run_id: str) -> WorkflowExecutionState | None:
        """Retrieve aggregate workflow run state by unique execution ID.

        Args:
            run_id: Unique identifier of the workflow run.

        Returns:
            The stored WorkflowExecutionState, or None if not found.
        """
        from sqlalchemy import select

        stmt = select(self._workflow_runs).where(self._workflow_runs.c.run_id == run_id)
        row = self._execute(stmt).mappings().one_or_none()
        if row is None:
            return None

        checkpoints = self.get_checkpoints(run_id)
        chk_dict = {chk.step_name: chk for chk in checkpoints}

        started = row["started_at"]
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        finished = row["finished_at"]
        if finished is not None and finished.tzinfo is None:
            finished = finished.replace(tzinfo=UTC)

        return WorkflowExecutionState(
            run_id=row["run_id"],
            workflow_name=row["workflow_name"],
            status=WorkflowStatus(row["status"]),
            started_at=started,
            finished_at=finished,
            current_stage=row["current_stage"],
            error_summary=row["error_summary"],
            step_checkpoints=chk_dict,
        )

    def list_runs(
        self, limit: int = 50, offset: int = 0
    ) -> list[WorkflowExecutionState]:
        """List workflow runs ordered by creation time descending.

        Args:
            limit: Maximum records to return.
            offset: Number of records to skip.

        Returns:
            List of WorkflowExecutionState instances.
        """
        from sqlalchemy import select

        stmt = (
            select(self._workflow_runs)
            .order_by(self._workflow_runs.c.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = self._execute(stmt).mappings().all()

        results: list[WorkflowExecutionState] = []
        for row in rows:
            run_id = row["run_id"]
            checkpoints = self.get_checkpoints(run_id)
            chk_dict = {chk.step_name: chk for chk in checkpoints}
            started = row["started_at"]
            if started.tzinfo is None:
                started = started.replace(tzinfo=UTC)
            finished = row["finished_at"]
            if finished is not None and finished.tzinfo is None:
                finished = finished.replace(tzinfo=UTC)

            results.append(
                WorkflowExecutionState(
                    run_id=run_id,
                    workflow_name=row["workflow_name"],
                    status=WorkflowStatus(row["status"]),
                    started_at=started,
                    finished_at=finished,
                    current_stage=row["current_stage"],
                    error_summary=row["error_summary"],
                    step_checkpoints=chk_dict,
                )
            )
        return results

    def save_checkpoint(self, checkpoint: CheckpointRecord) -> None:
        """Persist an individual step execution checkpoint.

        Args:
            checkpoint: The CheckpointRecord snapshot to store.
        """
        from sqlalchemy import select

        in_json = (
            json.dumps(checkpoint.input_payload)
            if checkpoint.input_payload is not None
            else None
        )
        out_json = (
            json.dumps(checkpoint.output_payload)
            if checkpoint.output_payload is not None
            else None
        )

        check_stmt = select(self._step_checkpoints.c.checkpoint_id).where(
            self._step_checkpoints.c.run_id == checkpoint.run_id,
            self._step_checkpoints.c.step_name == checkpoint.step_name,
        )
        existing = self._execute(check_stmt).scalar_one_or_none()

        values = {
            "stage_name": checkpoint.stage_name,
            "status": checkpoint.status.value,
            "attempt_number": checkpoint.attempt_number,
            "input_payload": in_json,
            "output_payload": out_json,
            "error_traceback": checkpoint.error_traceback,
            "started_at": checkpoint.started_at,
            "completed_at": checkpoint.completed_at,
        }

        if existing is not None:
            update_stmt = (
                self._step_checkpoints.update()
                .where(self._step_checkpoints.c.checkpoint_id == existing)
                .values(**values)
            )
            self._execute(update_stmt)
        else:
            values["checkpoint_id"] = checkpoint.checkpoint_id
            values["run_id"] = checkpoint.run_id
            values["step_name"] = checkpoint.step_name
            insert_stmt = self._step_checkpoints.insert().values(**values)
            self._execute(insert_stmt)

    def get_checkpoint(self, run_id: str, step_name: str) -> CheckpointRecord | None:
        """Retrieve the checkpoint for a specific step in a run.

        Args:
            run_id: Parent workflow execution ID.
            step_name: Unique step identifier within the workflow.

        Returns:
            The CheckpointRecord if found, else None.
        """
        from sqlalchemy import select

        stmt = select(self._step_checkpoints).where(
            self._step_checkpoints.c.run_id == run_id,
            self._step_checkpoints.c.step_name == step_name,
        )
        row = self._execute(stmt).mappings().one_or_none()
        if row is None:
            return None
        return self._map_checkpoint_row(row)

    def get_checkpoints(self, run_id: str) -> list[CheckpointRecord]:
        """Retrieve all recorded step checkpoints for a given workflow run.

        Args:
            run_id: Parent workflow execution ID.

        Returns:
            List of all CheckpointRecords recorded for this run, ordered by creation.
        """
        from sqlalchemy import select

        stmt = (
            select(self._step_checkpoints)
            .where(self._step_checkpoints.c.run_id == run_id)
            .order_by(self._step_checkpoints.c.started_at.asc())
        )
        rows = self._execute(stmt).mappings().all()
        return [self._map_checkpoint_row(r) for r in rows]

    def delete_checkpoints(self, run_id: str) -> None:
        """Delete all step checkpoints for a given workflow run.

        Args:
            run_id: Unique run ID.
        """
        stmt = self._step_checkpoints.delete().where(
            self._step_checkpoints.c.run_id == run_id
        )
        self._execute(stmt)

    @staticmethod
    def _map_checkpoint_row(row: Any) -> CheckpointRecord:
        """Deserialize a database row into a CheckpointRecord.

        Args:
            row: Database row mapping.

        Returns:
            Deserialized CheckpointRecord.
        """
        in_val = json.loads(row["input_payload"]) if row["input_payload"] else None
        out_val = json.loads(row["output_payload"]) if row["output_payload"] else None

        started = row["started_at"]
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)

        completed = row["completed_at"]
        if completed is not None and completed.tzinfo is None:
            completed = completed.replace(tzinfo=UTC)

        return CheckpointRecord(
            checkpoint_id=row["checkpoint_id"],
            run_id=row["run_id"],
            stage_name=row["stage_name"],
            step_name=row["step_name"],
            status=StepStatus(row["status"]),
            attempt_number=row["attempt_number"],
            input_payload=in_val,
            output_payload=out_val,
            error_traceback=row["error_traceback"],
            started_at=started,
            completed_at=completed,
        )
