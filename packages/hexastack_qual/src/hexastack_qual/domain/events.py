"""Domain events for hexastack-qual.

Notes/Architectural Intent:
    Encapsulates state transition facts emitted by quality audits, mutation
    testing runs, and statement formatting operations.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import ConfigDict, Field

from hexastack_core.domain import Event


class QualityGateFailedEvent(Event):
    """Emitted when one or more quality sanity checks fail.

    Notes/Architectural Intent:
        Enables distributed notification adapters (e.g. Apprise, Slack) to alert
        teams when architectural or code health standards are breached.
    """

    model_config = ConfigDict(frozen=True)

    target: str = Field(description="Target component or package.")
    failed_checks: list[str] = Field(description="Names of failing sanity checks.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of failure.",
    )


class CriticalMutantSurvivingEvent(Event):
    """Emitted when an actionable code mutant survives test suite execution.

    Notes/Architectural Intent:
        Alerts developers and AI agents that coverage-deficient test assertions
        exist and require fortification.
    """

    model_config = ConfigDict(frozen=True)

    package: str = Field(description="Target package name.")
    mutant_id: str = Field(description="Mutant identifier.")
    file_path: str = Field(description="Source file path.")
    line_number: int = Field(description="Source line number.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of discovery.",
    )


class AgentAssetDriftDetectedEvent(Event):
    """Emitted when local workspace agent assets deviate from universal templates.

    Notes/Architectural Intent:
        Signals that managed agent rules or workflows require synchronization.
    """

    model_config = ConfigDict(frozen=True)

    outdated_assets: list[str] = Field(description="List of out-of-sync agent assets.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of drift detection.",
    )


class StatementsFixedEvent(Event):
    """Emitted when __all__ statements are auto-formatted and sorted.

    Notes/Architectural Intent:
        Records an automated remediation event across targeted modules.
    """

    model_config = ConfigDict(frozen=True)

    target: str = Field(description="Target package or file.")
    files_modified: int = Field(description="Number of files modified.")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Timestamp of remediation.",
    )


__all__ = [
    "AgentAssetDriftDetectedEvent",
    "CriticalMutantSurvivingEvent",
    "QualityGateFailedEvent",
    "StatementsFixedEvent",
]
