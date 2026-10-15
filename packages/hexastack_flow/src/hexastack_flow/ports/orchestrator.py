"""Port interfaces defining CQRS workflow orchestration.

Notes/Architectural Intent:
    Establishes the primary inward-facing boundary for dispatching and managing
    hexaflow workflows within Hexastack applications. Decouples controllers
    and services from underlying execution engines and storage implementations.
"""

from abc import ABC, abstractmethod
from typing import Any

from hexaflow.domain.models import WorkflowDefinition

from hexastack_flow.domain.models import WorkflowExecutionResult

__all__ = [
    "CqrsWorkflowOrchestratorPort",
]


class CqrsWorkflowOrchestratorPort(ABC):
    """Abstract port for coordinating CQRS-driven workflow execution.

    Notes/Architectural Intent:
        Defines the high-level contract to execute, resume, or abort
        workflows backed by CQRS command/query buses and state stores.
    """

    @abstractmethod
    def execute(
        self,
        workflow: WorkflowDefinition,
        initial_inputs: dict[str, Any] | None = None,
    ) -> WorkflowExecutionResult:
        """Execute a workflow definition from the initial stage.

        Args:
            workflow: The workflow DAG definition to execute.
            initial_inputs: Optional dictionary of root arguments.

        Returns:
            WorkflowExecutionResult containing the terminal or suspension outcome.

        Raises:
            WorkflowError: If workflow validation or fatal execution failure occurs.
        """

    @abstractmethod
    def resume(
        self,
        run_id: str,
        workflow: WorkflowDefinition,
        patch_inputs: dict[str, Any] | None = None,
    ) -> WorkflowExecutionResult:
        """Resume a suspended workflow run from its latest checkpoints.

        Args:
            run_id: The unique identifier of the suspended workflow run.
            workflow: WorkflowDefinition matching the run.
            patch_inputs: Optional dictionary of replacement inputs for the resumed step.

        Returns:
            WorkflowExecutionResult reflecting post-resumption status.

        Raises:
            WorkflowNotFoundError: If run_id is not recorded in the state store.
            WorkflowError: If the workflow is not in a resumable state.
        """

    @abstractmethod
    def abort(
        self,
        run_id: str,
        workflow: WorkflowDefinition,
        reason: str = "Operator aborted",
    ) -> WorkflowExecutionResult:
        """Abort a workflow and unwind completed steps via compensation hooks.

        Args:
            run_id: The unique identifier of the workflow run to cancel.
            workflow: WorkflowDefinition containing compensation hooks.
            reason: Operator rationale or explanation for cancellation.

        Returns:
            WorkflowExecutionResult reflecting the aborted and compensated state.

        Raises:
            WorkflowNotFoundError: If run_id does not exist.
            WorkflowError: If rollback compensation encounters critical errors.
        """

    @abstractmethod
    def rewind(
        self,
        run_id: str,
        workflow: WorkflowDefinition,
        to_step: str,
        patch_inputs: dict[str, Any] | None = None,
        skip_steps: set[str] | list[str] | None = None,
    ) -> WorkflowExecutionResult:
        """Rewind workflow execution to before a step and re-evaluate downstream steps.

        Args:
            run_id: The unique identifier of the workflow run to rewind.
            workflow: WorkflowDefinition matching the run.
            to_step: The target step identifier to rewind before.
            patch_inputs: Optional override inputs for the resumed step frontier.
            skip_steps: Optional collection of step names to explicitly skip.

        Returns:
            WorkflowExecutionResult reflecting the state after time-travel replay.

        Raises:
            WorkflowNotFoundError: If run_id does not exist.
            WorkflowError: If to_step is invalid or rewind fails.
        """

    @abstractmethod
    def simulate(
        self,
        workflow: WorkflowDefinition,
        initial_inputs: dict[str, Any] | None = None,
        allow_unsafe: bool = False,
        fault_injection: dict[str, Exception] | None = None,
    ) -> WorkflowExecutionResult:
        """Perform a dry-run simulation of the workflow DAG without side effects.

        Args:
            workflow: The workflow DAG definition to simulate.
            initial_inputs: Optional dictionary of root arguments.
            allow_unsafe: When True, executes side-effecting steps without mocks.
            fault_injection: Optional mapping of step names to simulated Exceptions.

        Returns:
            WorkflowExecutionResult summarizing the simulated outcome.

        Raises:
            WorkflowError: If simulation validation or fatal error occurs.
        """

    @abstractmethod
    def render(
        self,
        workflow: WorkflowDefinition,
        format_name: str = "mermaid",
        options: Any | None = None,
    ) -> str:
        """Render the workflow DAG into a visual diagram or structural format.

        Args:
            workflow: The workflow DAG definition to visualize.
            format_name: Name of renderer format ('mermaid', 'dot', 'ascii', 'json').
            options: Optional renderer options (direction, critical path, highlight nodes).

        Returns:
            Rendered diagram or structured output string.
        """

    @abstractmethod
    def close(self) -> None:
        """Release underlying engine worker pools and execution resources.

        Notes/Architectural Intent:
            Ensures child worker processes and threads allocated by the underlying
            execution engine are gracefully shut down.
        """

    async def aclose(self) -> None:
        """Asynchronously release underlying engine worker pools and resources.

        Notes/Architectural Intent:
            Delegates to close() by default to provide an async cleanup entrypoint.
        """
        self.close()
