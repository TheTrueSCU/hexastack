"""Hexagonal architecture boundary tests for hexastack_db."""

from pytest_archon import archrule


def test_domain_boundary_rules():
    (
        archrule("Domain layer must not import from forbidden layers")
        .match("hexastack_db.domain")
        .should_not_import("hexastack_db.adapters", "hexastack_db.infra")
        .check("hexastack_db")
    )
