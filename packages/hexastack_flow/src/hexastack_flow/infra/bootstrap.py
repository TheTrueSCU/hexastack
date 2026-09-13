"""Bootstrap extension registering Hexastack workflow orchestration runtime.

Notes/Architectural Intent:
    Implements BootstrapperPort for hexastack-flow, wiring CqrsWorkflowRunner
    into the dependency injection container and exposing orchestration services.
"""

from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_flow.adapters.cqrs.runner import CqrsWorkflowRunner
from hexastack_flow.ports.orchestrator import CqrsWorkflowOrchestratorPort

__all__ = [
    "FlowBootstrapper",
]


class FlowBootstrapper(BootstrapperPort):
    """Bootstrap extension configuring workflow orchestration runtime.

    Notes/Architectural Intent:
        Registers CqrsWorkflowOrchestratorPort implementation in the DI container,
        resolving optional event bus and state store instances if present.
    """

    name: str = "flow"
    order: int = 35

    def configure(self, context: BootstrapContext) -> None:
        """Phase 2: Assemble workflow runner and register in container.

        Args:
            context: BootstrapContext containing DI container and configuration.
        """
        di = context.container

        event_bus: EventBusPort | None = None
        if EventBusPort in di:
            event_bus = di.resolve(EventBusPort)

        runner = CqrsWorkflowRunner(event_bus=event_bus)
        di.add_instance(runner, declared_class=CqrsWorkflowOrchestratorPort)
        context.properties["flow_runner"] = runner

    def register_config(self, registry: ConfigRegistry) -> None:
        """Phase 1: Register workflow configuration schemas.

        Args:
            registry: Target ConfigRegistry instance.
        """
        # Reserved for future flow-specific configuration schemas
