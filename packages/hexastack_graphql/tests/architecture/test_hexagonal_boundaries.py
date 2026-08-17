"""Hexagonal architecture boundary tests for hexastack_graphql."""

from pytest_archon import archrule


def test_domain_boundary_rules():
    (
        archrule("Domain layer must not import from forbidden layers")
        .match("hexastack_graphql.domain")
        .should_not_import("hexastack_graphql.adapters", "hexastack_graphql.infra")
        .check("hexastack_graphql")
    )
