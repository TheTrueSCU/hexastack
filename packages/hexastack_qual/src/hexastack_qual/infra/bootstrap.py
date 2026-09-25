"""Bootstrap extension registering Hexastack quality and governance runtime.

Notes/Architectural Intent:
    Implements BootstrapperPort for hexastack-qual, wiring HexaqualRunnerAdapter
    and CQRS handlers into the dependency injection container.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hexastack_core.ports.bootstrap import BootstrapperPort
from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_qual.adapters.cqrs.handlers import (
    FormatStatementsHandler,
    GetPrHealthHandler,
    GetQualityScorecardHandler,
    GetTestImpactHandler,
    InspectMutantsHandler,
    RunMutationTestingHandler,
    RunSanityCheckHandler,
    SyncAgentAssetsHandler,
)
from hexastack_qual.adapters.hexaqual.runner import HexaqualRunnerAdapter
from hexastack_qual.ports.auditor import QualityAuditorPort
from hexastack_qual.ports.diagnostics import PrDiagnosticPort
from hexastack_qual.ports.mutator import MutationInspectorPort

if TYPE_CHECKING:
    from hexastack_core.infra.bootstrap import BootstrapContext
    from hexastack_core.infra.registries.config import ConfigRegistry


class QualBootstrapper(BootstrapperPort):
    """Bootstrap extension configuring quality and governance runtime.

    Notes/Architectural Intent:
        Registers QualityAuditorPort, MutationInspectorPort, and PrDiagnosticPort
        implementations and their corresponding CQRS handlers into rodi.
    """

    name: str = "qual"
    order: int = 36

    def configure(self, context: BootstrapContext) -> None:
        """Phase 2: Assemble quality runner and register in container.

        Args:
            context: BootstrapContext containing DI container and configuration.
        """
        di = context.container

        event_bus: EventBusPort | None = None
        if EventBusPort in di:
            event_bus = di.resolve(EventBusPort)

        runner = HexaqualRunnerAdapter()
        di.add_instance(runner, declared_class=QualityAuditorPort)
        di.add_instance(runner, declared_class=MutationInspectorPort)
        di.add_instance(runner, declared_class=PrDiagnosticPort)

        # Register handlers
        di.add_instance(
            RunSanityCheckHandler(auditor=runner, event_bus=event_bus),
            declared_class=RunSanityCheckHandler,
        )
        di.add_instance(
            FormatStatementsHandler(auditor=runner, event_bus=event_bus),
            declared_class=FormatStatementsHandler,
        )
        di.add_instance(
            RunMutationTestingHandler(mutator=runner),
            declared_class=RunMutationTestingHandler,
        )
        di.add_instance(
            SyncAgentAssetsHandler(),
            declared_class=SyncAgentAssetsHandler,
        )
        di.add_instance(
            GetQualityScorecardHandler(auditor=runner),
            declared_class=GetQualityScorecardHandler,
        )
        di.add_instance(
            InspectMutantsHandler(mutator=runner),
            declared_class=InspectMutantsHandler,
        )
        di.add_instance(
            GetTestImpactHandler(diagnostics=runner),
            declared_class=GetTestImpactHandler,
        )
        di.add_instance(
            GetPrHealthHandler(diagnostics=runner),
            declared_class=GetPrHealthHandler,
        )

        context.properties["qual_runner"] = runner

    def register_config(self, registry: ConfigRegistry) -> None:
        """Phase 1: Register quality configuration schemas.

        Args:
            registry: Target ConfigRegistry instance.
        """


__all__ = [
    "QualBootstrapper",
]
