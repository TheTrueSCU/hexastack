"""Hexagonal architecture boundary tests for hexastack_cqrs."""

from pytest_archon import archrule


def test_domain_boundary_rules():
    (
        archrule("Domain layer must not import from forbidden layers")
        .match("hexastack_cqrs.domain")
        .should_not_import(
            "hexastack_cqrs.ports", "hexastack_cqrs.adapters", "hexastack_cqrs.infra"
        )
        .check("hexastack_cqrs")
    )


def test_ports_boundary_rules():
    (
        archrule("Ports layer must not import from forbidden layers")
        .match("hexastack_cqrs.ports")
        .should_not_import("hexastack_cqrs.adapters", "hexastack_cqrs.infra")
        .check("hexastack_cqrs")
    )
