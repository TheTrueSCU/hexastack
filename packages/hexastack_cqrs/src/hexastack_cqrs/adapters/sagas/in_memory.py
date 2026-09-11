"""In-memory synchronous and asynchronous distributed saga orchestrator adapter.

Notes/Architectural Intent:
    Provides a self-contained, in-process saga coordinator executing forward actions
    and automatically orchestrating reverse compensating transactions upon failure.
    Requires no external orchestrator infrastructure, enabling deterministic testing
    and lightweight distributed transactions.
"""

import inspect
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from hexastack_core.domain.command import Command
from hexastack_cqrs.domain.sagas import (
    SagaCompensationError,
    SagaDefinition,
    SagaError,
    SagaResult,
    SagaState,
    SagaStatus,
    SagaStep,
)
from hexastack_cqrs.ports.buses import CommandBusPort
from hexastack_cqrs.ports.sagas import (
    SagaOrchestratorPort,
    SagaStoragePort,
)


class InMemorySagaStorage(SagaStoragePort):
    """In-memory thread-safe implementation of SagaStoragePort for testing and local execution.

    Notes/Architectural Intent:
        Stores saga states in a dictionary indexed by saga ID, allowing state inspection
        during and after workflow execution.
    """

    def __init__(self) -> None:
        """Initialize empty saga storage."""
        self._states: dict[str, SagaState] = {}

    def save_state(self, state: SagaState) -> None:
        """Persist or update saga state.

        Args:
            state: The SagaState snapshot to store.
        """
        self._states[state.saga_id] = state

    def get_state(self, saga_id: str) -> SagaState | None:
        """Retrieve saga state by ID.

        Args:
            saga_id: Unique saga execution ID.

        Returns:
            SagaState if found, None otherwise.
        """
        return self._states.get(saga_id)

    def clear(self) -> None:
        """Clear all stored states."""
        self._states.clear()


class InMemorySagaOrchestrator(SagaOrchestratorPort):
    """In-process coordinator for executing multi-step sagas with automated compensation.

    Notes/Architectural Intent:
        Iterates sequentially through defined SagaSteps, routing forward commands to the
        CommandBusPort or invoking step callables. If any step fails, automatically halts
        forward execution and executes compensating actions in strict reverse (LIFO) order.
    """

    def __init__(
        self,
        command_bus: CommandBusPort | None = None,
        storage: SagaStoragePort | None = None,
    ) -> None:
        """Initialize in-memory saga orchestrator.

        Args:
            command_bus: Optional CommandBusPort for dispatching Command instances.
            storage: Optional SagaStoragePort for recording state transitions.
        """
        self._command_bus = command_bus
        self._storage = storage or InMemorySagaStorage()

    @property
    def storage(self) -> SagaStoragePort:
        """Access the underlying saga state storage."""
        return self._storage

    def execute(
        self,
        saga: SagaDefinition,
        initial_state: dict[str, Any] | None = None,
    ) -> SagaResult:
        """Execute saga steps sequentially, triggering LIFO compensations on failure.

        Args:
            saga: The immutable SagaDefinition specification.
            initial_state: Optional dictionary containing initial input parameters.

        Returns:
            SagaResult reflecting COMPLETED or COMPENSATED status.

        Raises:
            SagaCompensationError: If a compensating action fails during rollback.
            SagaError: If coordination encounters an unrecoverable failure.
        """
        start_time = time.perf_counter()
        saga_id = str(uuid4())
        state = SagaState(
            saga_id=saga_id,
            saga_name=saga.name,
            status=SagaStatus.RUNNING,
            step_results=dict(initial_state) if initial_state else {},
        )
        self._storage.save_state(state)

        executed_steps: list[tuple[SagaStep, Any]] = []

        try:
            for idx, step in enumerate(saga.steps):
                state.current_step_index = idx
                step_result = self._execute_step_action(step, state.step_results)
                state.step_results[step.name] = step_result
                executed_steps.append((step, step_result))
                self._storage.save_state(state)

            state.status = SagaStatus.COMPLETED
            state.finished_at = datetime.now(UTC)
            self._storage.save_state(state)

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return SagaResult(
                saga_id=state.saga_id,
                saga_name=saga.name,
                status=SagaStatus.COMPLETED,
                step_results=state.step_results,
                compensated=False,
                execution_duration_ms=duration_ms,
            )

        except Exception as exc:
            state.status = SagaStatus.COMPENSATING
            state.error = str(exc)
            self._storage.save_state(state)

            self._run_compensations(executed_steps, state)

            state.status = SagaStatus.COMPENSATED
            state.finished_at = datetime.now(UTC)
            self._storage.save_state(state)

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return SagaResult(
                saga_id=state.saga_id,
                saga_name=saga.name,
                status=SagaStatus.COMPENSATED,
                step_results=state.step_results,
                error=str(exc),
                compensated=True,
                compensated_steps=list(state.compensated_steps),
                execution_duration_ms=duration_ms,
            )

    async def execute_async(
        self,
        saga: SagaDefinition,
        initial_state: dict[str, Any] | None = None,
    ) -> SagaResult:
        """Execute saga steps asynchronously in an event loop.

        Args:
            saga: The immutable SagaDefinition specification.
            initial_state: Optional dictionary containing initial input parameters.

        Returns:
            SagaResult reflecting COMPLETED or COMPENSATED status.

        Raises:
            SagaCompensationError: If a compensating action fails during rollback.
            SagaError: If coordination encounters an unrecoverable failure.
        """
        start_time = time.perf_counter()
        saga_id = str(uuid4())
        state = SagaState(
            saga_id=saga_id,
            saga_name=saga.name,
            status=SagaStatus.RUNNING,
            step_results=dict(initial_state) if initial_state else {},
        )
        self._storage.save_state(state)

        executed_steps: list[tuple[SagaStep, Any]] = []

        try:
            for idx, step in enumerate(saga.steps):
                state.current_step_index = idx
                step_result = await self._execute_step_action_async(
                    step, state.step_results
                )
                state.step_results[step.name] = step_result
                executed_steps.append((step, step_result))
                self._storage.save_state(state)

            state.status = SagaStatus.COMPLETED
            state.finished_at = datetime.now(UTC)
            self._storage.save_state(state)

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return SagaResult(
                saga_id=state.saga_id,
                saga_name=saga.name,
                status=SagaStatus.COMPLETED,
                step_results=state.step_results,
                compensated=False,
                execution_duration_ms=duration_ms,
            )

        except Exception as exc:
            state.status = SagaStatus.COMPENSATING
            state.error = str(exc)
            self._storage.save_state(state)

            await self._run_compensations_async(executed_steps, state)

            state.status = SagaStatus.COMPENSATED
            state.finished_at = datetime.now(UTC)
            self._storage.save_state(state)

            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return SagaResult(
                saga_id=state.saga_id,
                saga_name=saga.name,
                status=SagaStatus.COMPENSATED,
                step_results=state.step_results,
                error=str(exc),
                compensated=True,
                compensated_steps=list(state.compensated_steps),
                execution_duration_ms=duration_ms,
            )

    def _execute_step_action(self, step: SagaStep, context: dict[str, Any]) -> Any:
        """Dispatch or invoke step forward action."""
        action = step.action
        if isinstance(action, Command) and self._command_bus is not None:
            return self._command_bus.dispatch(action)

        if callable(action):
            sig = inspect.signature(action)
            if len(sig.parameters) == 0:
                return action()
            if len(sig.parameters) == 1:
                return action(context)
            return action(context, step)

        if isinstance(action, Command):
            raise SagaError(
                f"Step '{step.name}' configured with Command '{action.__class__.__name__}' "
                "but no CommandBusPort provided to orchestrator."
            )

        return action

    async def _execute_step_action_async(
        self, step: SagaStep, context: dict[str, Any]
    ) -> Any:
        """Dispatch or invoke step forward action in async context."""
        action = step.action
        if isinstance(action, Command) and self._command_bus is not None:
            res = self._command_bus.dispatch(action)
            if inspect.isawaitable(res):
                return await res
            return res

        if callable(action):
            sig = inspect.signature(action)
            if len(sig.parameters) == 0:
                res = action()
            elif len(sig.parameters) == 1:
                res = action(context)
            else:
                res = action(context, step)

            if inspect.isawaitable(res):
                return await res
            return res

        if isinstance(action, Command):
            raise SagaError(
                f"Step '{step.name}' configured with Command '{action.__class__.__name__}' "
                "but no CommandBusPort provided to orchestrator."
            )

        return action

    def _run_compensations(
        self,
        executed_steps: list[tuple[SagaStep, Any]],
        state: SagaState,
    ) -> None:
        """Unwind compensations in strict LIFO order."""
        for step, forward_result in reversed(executed_steps):
            if step.compensation is None:
                continue

            try:
                comp = step.compensation
                if isinstance(comp, Command) and self._command_bus is not None:
                    self._command_bus.dispatch(comp)
                elif callable(comp):
                    sig = inspect.signature(comp)
                    if len(sig.parameters) == 0:
                        comp()
                    elif len(sig.parameters) == 1:
                        comp(forward_result)
                    else:
                        comp(forward_result, state.step_results)

                state.compensated_steps.append(step.name)
                self._storage.save_state(state)

            except Exception as comp_exc:
                state.status = SagaStatus.FAILED
                state.error = f"Compensation failed on step '{step.name}': {comp_exc}"
                self._storage.save_state(state)
                raise SagaCompensationError(state.error) from comp_exc

    async def _run_compensations_async(
        self,
        executed_steps: list[tuple[SagaStep, Any]],
        state: SagaState,
    ) -> None:
        """Unwind compensations asynchronously in strict LIFO order."""
        for step, forward_result in reversed(executed_steps):
            if step.compensation is None:
                continue

            try:
                comp = step.compensation
                if isinstance(comp, Command) and self._command_bus is not None:
                    res = self._command_bus.dispatch(comp)
                    if inspect.isawaitable(res):
                        await res
                elif callable(comp):
                    sig = inspect.signature(comp)
                    if len(sig.parameters) == 0:
                        res = comp()
                    elif len(sig.parameters) == 1:
                        res = comp(forward_result)
                    else:
                        res = comp(forward_result, state.step_results)

                    if inspect.isawaitable(res):
                        await res

                state.compensated_steps.append(step.name)
                self._storage.save_state(state)

            except Exception as comp_exc:
                state.status = SagaStatus.FAILED
                state.error = f"Compensation failed on step '{step.name}': {comp_exc}"
                self._storage.save_state(state)
                raise SagaCompensationError(state.error) from comp_exc


__all__ = [
    "InMemorySagaOrchestrator",
    "InMemorySagaStorage",
]
