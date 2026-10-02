"""Ports module for hexastack_flags.

Notes/Architectural Intent:
    Re-exports FeatureFlagPort from hexastack_core for hexagonal boundary consistency.
"""

from hexastack_core.ports.feature_flags import FeatureFlagPort

__all__ = [
    "FeatureFlagPort",
]
