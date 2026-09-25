"""Unit tests for hexastack-qual domain events.

Notes/Architectural Intent:
    Validates domain event instantiation, timestamp generation, and immutability.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from hexastack_qual.domain.events import (
    AgentAssetDriftDetectedEvent,
    CriticalMutantSurvivingEvent,
    QualityGateFailedEvent,
    StatementsFixedEvent,
)
from pydantic import ValidationError


def test_quality_gate_failed_event() -> None:
    """Ensure QualityGateFailedEvent records target and failed checks."""
    event = QualityGateFailedEvent(
        target="hexastack-core",
        failed_checks=["Cognitive Complexity", "Test Parity"],
    )
    assert event.target == "hexastack-core"
    assert len(event.failed_checks) == 2
    assert isinstance(event.timestamp, datetime)

    attr_name = "target"
    with pytest.raises(ValidationError):
        setattr(event, attr_name, "other")


def test_critical_mutant_surviving_event() -> None:
    """Ensure CriticalMutantSurvivingEvent records coordinates."""
    event = CriticalMutantSurvivingEvent(
        package="cqrs",
        mutant_id="m-404",
        file_path="src/cqrs/pipeline.py",
        line_number=99,
    )
    assert event.package == "cqrs"
    assert event.mutant_id == "m-404"
    assert event.file_path == "src/cqrs/pipeline.py"
    assert event.line_number == 99
    assert isinstance(event.timestamp, datetime)


def test_agent_asset_drift_detected_event() -> None:
    """Ensure AgentAssetDriftDetectedEvent lists outdated assets."""
    outdated = [".agents/rules/hexaqual-documentation.md"]
    event = AgentAssetDriftDetectedEvent(outdated_assets=outdated)
    assert event.outdated_assets == outdated
    assert isinstance(event.timestamp, datetime)


def test_statements_fixed_event() -> None:
    """Ensure StatementsFixedEvent records target and count."""
    event = StatementsFixedEvent(target="hexastack-ai", files_modified=3)
    assert event.target == "hexastack-ai"
    assert event.files_modified == 3
    assert isinstance(event.timestamp, datetime)
