"""Unit tests for QualityEventPublisherAdapter.

Notes/Architectural Intent:
    Verifies that domain events are correctly instantiated and dispatched
    across the CQRS EventBusPort.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from hexastack_qual.adapters.events.publisher import QualityEventPublisherAdapter
from hexastack_qual.domain.events import (
    AgentAssetDriftDetectedEvent,
    CriticalMutantSurvivingEvent,
    QualityGateFailedEvent,
    StatementsFixedEvent,
)

from hexastack_cqrs.ports.buses import EventBusPort


def test_publish_quality_gate_failed():
    """Verify QualityGateFailedEvent is dispatched with expected fields."""
    mock_bus = MagicMock(spec=EventBusPort)
    publisher = QualityEventPublisherAdapter(mock_bus)

    publisher.publish_quality_gate_failed(
        target="core",
        failed_checks=["ruff", "ty"],
    )

    published_event = mock_bus.publish.call_args[0][0]
    assert isinstance(published_event, QualityGateFailedEvent)
    assert published_event.target == "core"
    assert published_event.failed_checks == ["ruff", "ty"]


def test_publish_critical_mutant_surviving():
    """Verify CriticalMutantSurvivingEvent is dispatched with mutant coordinates."""
    mock_bus = MagicMock(spec=EventBusPort)
    publisher = QualityEventPublisherAdapter(mock_bus)

    publisher.publish_critical_mutant_surviving(
        package="cqrs",
        mutant_id="mutant-42",
        file_path="src/cqrs/bus.py",
        line_number=105,
    )

    published_event = mock_bus.publish.call_args[0][0]
    assert isinstance(published_event, CriticalMutantSurvivingEvent)
    assert published_event.package == "cqrs"
    assert published_event.mutant_id == "mutant-42"
    assert published_event.file_path == "src/cqrs/bus.py"
    assert published_event.line_number == 105


def test_publish_statements_fixed():
    """Verify StatementsFixedEvent is dispatched with file count."""
    mock_bus = MagicMock(spec=EventBusPort)
    publisher = QualityEventPublisherAdapter(mock_bus)

    publisher.publish_statements_fixed(
        target="workspace",
        files_modified=4,
    )

    published_event = mock_bus.publish.call_args[0][0]
    assert isinstance(published_event, StatementsFixedEvent)
    assert published_event.target == "workspace"
    assert published_event.files_modified == 4


def test_publish_agent_asset_drift():
    """Verify AgentAssetDriftDetectedEvent is dispatched with asset list."""
    mock_bus = MagicMock(spec=EventBusPort)
    publisher = QualityEventPublisherAdapter(mock_bus)

    publisher.publish_agent_asset_drift(
        outdated_assets=[".agents/rules/hexaqual-docstrings.md"],
    )

    published_event = mock_bus.publish.call_args[0][0]
    assert isinstance(published_event, AgentAssetDriftDetectedEvent)
    assert published_event.outdated_assets == [".agents/rules/hexaqual-docstrings.md"]
