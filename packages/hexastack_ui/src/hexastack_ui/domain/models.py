"""Domain models for UI presentations and DevTools state.

Notes/Architectural Intent:
    Pure domain representations of diagnostic records, CQRS messages,
    service bindings, and UI dashboard state independent of any UI framework.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "CQRSMessageSummary",
    "DevToolsDashboardState",
    "FeatureFlagSummary",
    "ServiceBindingSummary",
]


class CQRSMessageSummary(BaseModel):
    """Summary of a registered CQRS Command or Query contract.

    Notes/Architectural Intent:
        Represents message metadata for visual exploration across developer dashboards.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(
        description="Canonical class or registration name of the CQRS message"
    )
    message_type: str = Field(description="Type of message ('Command' or 'Query')")
    module: str = Field(
        default="", description="Originating module of the message definition"
    )


class FeatureFlagSummary(BaseModel):
    """Summary of an active feature flag and its current state.

    Notes/Architectural Intent:
        Encapsulates feature flag key/value status for dashboard toggling and inspection.
    """

    model_config = ConfigDict(frozen=True)

    key: str = Field(description="Unique identifier key of the feature flag")
    enabled: bool = Field(description="Boolean enabled status of the flag")
    description: str = Field(
        default="", description="Optional human-readable description"
    )


class ServiceBindingSummary(BaseModel):
    """Summary of a dependency injection service registration.

    Notes/Architectural Intent:
        Represents service lifetime, interface, and concrete implementation binding metadata.
    """

    model_config = ConfigDict(frozen=True)

    service: str = Field(description="Service interface or class name")
    module: str = Field(
        default="", description="Module path where the service is defined"
    )
    resolver: str = Field(
        default="", description="Binding description or lifetime resolution strategy"
    )


class DevToolsDashboardState(BaseModel):
    """Aggregated snapshot of Hexastack runtime state for DevTools inspection.

    Notes/Architectural Intent:
        Immutable aggregate containing all diagnostic summaries for UI rendering.
    """

    model_config = ConfigDict(frozen=True)

    commands: list[CQRSMessageSummary] = Field(
        default_factory=list, description="Registered commands"
    )
    queries: list[CQRSMessageSummary] = Field(
        default_factory=list, description="Registered queries"
    )
    flags: list[FeatureFlagSummary] = Field(
        default_factory=list, description="Active feature flags"
    )
    services: list[ServiceBindingSummary] = Field(
        default_factory=list, description="Registered DI services"
    )
    middlewares: list[str] = Field(
        default_factory=list, description="Active middleware pipeline names"
    )
