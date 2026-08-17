"""Hexagonal architecture boundary tests for hexastack."""

from pytest_archon import archrule


def test_domain_boundary_rules():
    (
        archrule("Domain layer must not import from forbidden layers")
        .match("hexastack.domain")
        .should_not_import("hexastack.adapters")
        .check("hexastack")
    )
