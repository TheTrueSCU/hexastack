"""CQRS queries for hexastack-qual.

Notes/Architectural Intent:
    Encapsulates read-only inspections for quality scorecards, mutant reports,
    git test impact, and PR diagnostics.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field

from hexastack_core.domain import Query
from hexastack_qual.domain.models import (
    MutantReport,
    PrHealthSummary,
    QualityScorecard,
)


class GetQualityScorecardQuery(Query[QualityScorecard]):
    """Query to retrieve quality health metrics and sanity status.

    Notes/Architectural Intent:
        Produces a comprehensive scorecard without side-effects.
    """

    model_config = ConfigDict(frozen=True)

    package: str | None = Field(
        default=None,
        description="Target package name or None for workspace.",
    )
    skip_tests: bool = Field(
        default=True,
        description="Whether to skip unit test suites.",
    )


class InspectMutantsQuery(Query[MutantReport]):
    """Query to inspect surviving mutants and triage classifications.

    Notes/Architectural Intent:
        Reads mutation cache and classifies surviving mutants without running tests.
    """

    model_config = ConfigDict(frozen=True)

    package: str | None = Field(
        default=None,
        description="Target package name or None for workspace.",
    )
    actionable_only: bool = Field(
        default=True,
        description="If True, filters only critical actionable mutants.",
    )


class GetTestImpactQuery(Query[list[str]]):
    """Query to compute test suites impacted by git diff changes.

    Notes/Architectural Intent:
        Identifies impacted test targets to enable smart scoped testing.
    """

    model_config = ConfigDict(frozen=True)

    base_ref: str = Field(
        default="origin/main",
        description="Git base reference or branch.",
    )


class GetPrHealthQuery(Query[PrHealthSummary]):
    """Query to inspect pull request CI checks, CodeQL alerts, and review threads.

    Notes/Architectural Intent:
        Fetches GitHub PR diagnostic state.
    """

    model_config = ConfigDict(frozen=True)

    pr_number: int = Field(description="GitHub pull request number.")


__all__ = [
    "GetPrHealthQuery",
    "GetQualityScorecardQuery",
    "GetTestImpactQuery",
    "InspectMutantsQuery",
]
