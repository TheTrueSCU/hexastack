"""Hexagonal architecture boundary tests for hexastack_mcp."""

from pytest_archon import archrule


def test_domain_boundary_rules():
    (
        archrule("Domain layer must not import from forbidden layers")
        .match("hexastack_mcp.domain")
        .should_not_import("hexastack_mcp.adapters", "hexastack_mcp.infra")
        .check("hexastack_mcp")
    )
