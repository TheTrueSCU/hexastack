"""Domain layer models, exceptions, and events for hexastack-qual.

Notes/Architectural Intent:
    Pure domain entities representing code metrics, sanity results, and quality
    failure events with zero infrastructure dependencies.
"""

from __future__ import annotations

from hexastack_qual.domain.events import (
    AgentAssetDriftDetectedEvent,
    CriticalMutantSurvivingEvent,
    QualityGateFailedEvent,
    StatementsFixedEvent,
)
from hexastack_qual.domain.exceptions import (
    AdapterNotAvailableError,
    ComplexityExceededError,
    ParityViolationError,
    QualityError,
    QualityGateFailedError,
    StatementIntegrityError,
)
from hexastack_qual.domain.models import (
    ComplexityMetric,
    MutantFinding,
    MutantReport,
    ParityFinding,
    PrHealthSummary,
    QualityCheckResult,
    QualityScorecard,
    StatementFinding,
)

__all__ = [
    "AdapterNotAvailableError",
    "AgentAssetDriftDetectedEvent",
    "ComplexityExceededError",
    "ComplexityMetric",
    "CriticalMutantSurvivingEvent",
    "MutantFinding",
    "MutantReport",
    "ParityFinding",
    "ParityViolationError",
    "PrHealthSummary",
    "QualityCheckResult",
    "QualityError",
    "QualityGateFailedError",
    "QualityGateFailedEvent",
    "QualityScorecard",
    "StatementFinding",
    "StatementIntegrityError",
    "StatementsFixedEvent",
]
