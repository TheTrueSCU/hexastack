"""Event publisher adapter for hexastack-qual domain events.

Notes/Architectural Intent:
    Provides convenience methods for emitting quality gate failures, mutant
    survival notices, and asset drift notifications across the CQRS EventBusPort.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hexastack_qual.domain.events import (
    AgentAssetDriftDetectedEvent,
    CriticalMutantSurvivingEvent,
    QualityGateFailedEvent,
    StatementsFixedEvent,
)

if TYPE_CHECKING:
    from hexastack_cqrs.ports.buses import EventBusPort


class QualityEventPublisherAdapter:
    """Adapter publishing quality domain events across the CQRS event bus.

    Notes/Architectural Intent:
        Encapsulates event instantiation and publishing to decouple caller logic
        from specific event models.
    """

    def __init__(self, event_bus: EventBusPort) -> None:
        """Initialize publisher with event bus.

        Args:
            event_bus: The CQRS EventBusPort implementation.
        """
        self._event_bus = event_bus

    def publish_quality_gate_failed(
        self,
        target: str,
        failed_checks: list[str],
    ) -> None:
        """Publish QualityGateFailedEvent when checks fail.

        Args:
            target: Target component or package.
            failed_checks: List of failing sanity check names.
        """
        event = QualityGateFailedEvent(target=target, failed_checks=failed_checks)
        self._event_bus.publish(event)

    def publish_critical_mutant_surviving(
        self,
        package: str,
        mutant_id: str,
        file_path: str,
        line_number: int,
    ) -> None:
        """Publish CriticalMutantSurvivingEvent when an actionable mutant survives.

        Args:
            package: Target package name.
            mutant_id: Identifier of surviving mutant.
            file_path: Source file path where mutation occurred.
            line_number: Line number of mutation.
        """
        event = CriticalMutantSurvivingEvent(
            package=package,
            mutant_id=mutant_id,
            file_path=file_path,
            line_number=line_number,
        )
        self._event_bus.publish(event)

    def publish_statements_fixed(
        self,
        target: str,
        files_modified: int,
    ) -> None:
        """Publish StatementsFixedEvent when files are auto-formatted.

        Args:
            target: Target component or workspace.
            files_modified: Number of files modified.
        """
        event = StatementsFixedEvent(target=target, files_modified=files_modified)
        self._event_bus.publish(event)

    def publish_agent_asset_drift(
        self,
        outdated_assets: list[str],
    ) -> None:
        """Publish AgentAssetDriftDetectedEvent when agent assets drift.

        Args:
            outdated_assets: List of outdated agent asset paths.
        """
        event = AgentAssetDriftDetectedEvent(outdated_assets=outdated_assets)
        self._event_bus.publish(event)


__all__ = [
    "QualityEventPublisherAdapter",
]
