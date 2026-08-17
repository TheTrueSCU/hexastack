"""Hexagonal architecture boundary tests for hexastack_ai."""

from pytest_archon import archrule


def test_domain_boundary_rules():
    (
        archrule("Domain layer must not import from forbidden layers")
        .match("hexastack_ai.domain")
        .should_not_import("hexastack_ai.adapters", "hexastack_ai.infra")
        .check("hexastack_ai")
    )
