"""Hexagonal architecture boundary tests for hexastack_auth."""

from pytest_archon import archrule


def test_domain_boundary_rules():
    (
        archrule("Domain layer must not import from forbidden layers")
        .match("hexastack_auth.domain")
        .should_not_import(
            "hexastack_auth.ports", "hexastack_auth.adapters", "hexastack_auth.infra"
        )
        .check("hexastack_auth")
    )


def test_ports_boundary_rules():
    (
        archrule("Ports layer must not import from forbidden layers")
        .match("hexastack_auth.ports")
        .should_not_import("hexastack_auth.adapters", "hexastack_auth.infra")
        .check("hexastack_auth")
    )
