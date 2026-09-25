"""Unit tests for CQRS queries.

Notes/Architectural Intent:
    Validates CQRS query instantiation and field immutability.
"""

from __future__ import annotations

import pytest
from hexastack_qual.adapters.cqrs.queries import (
    GetPrHealthQuery,
    GetQualityScorecardQuery,
    GetTestImpactQuery,
    InspectMutantsQuery,
)
from pydantic import ValidationError


def test_get_quality_scorecard_query() -> None:
    """Ensure GetQualityScorecardQuery sets attributes."""
    query = GetQualityScorecardQuery(package="db", skip_tests=False)
    assert query.package == "db"
    assert query.skip_tests is False

    attr_name = "package"
    with pytest.raises(ValidationError):
        setattr(query, attr_name, "other")


def test_inspect_mutants_query() -> None:
    """Ensure InspectMutantsQuery captures package and actionable_only."""
    query = InspectMutantsQuery(package="events", actionable_only=True)
    assert query.package == "events"
    assert query.actionable_only is True


def test_get_test_impact_query() -> None:
    """Ensure GetTestImpactQuery records base reference."""
    query = GetTestImpactQuery(base_ref="HEAD~1")
    assert query.base_ref == "HEAD~1"


def test_get_pr_health_query() -> None:
    """Ensure GetPrHealthQuery stores PR number."""
    query = GetPrHealthQuery(pr_number=33)
    assert query.pr_number == 33
