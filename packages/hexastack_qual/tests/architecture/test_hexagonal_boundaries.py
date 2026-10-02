"""Hexagonal architecture boundary tests for hexastack_qual.

Notes/Architectural Intent:
    Verifies that domain and ports layers do not import from adapters or infra,
    and that adapters do not import from infra, strictly enforcing hexagonal
    invariants.
"""

from hexastack_core.testing import assert_clean_architecture


def test_hexastack_qual_clean_architecture():
    """Assert hexastack_qual strictly complies with Hexagonal layer isolation."""
    assert_clean_architecture("hexastack_qual")
