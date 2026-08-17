"""Hexagonal architecture boundary tests for hexastack_otel."""

from pytest_archon import archrule


def test_domain_boundary_rules():
    (
        archrule("Domain layer must not import from forbidden layers")
        .match("hexastack_otel.domain")
        .should_not_import(
            "hexastack_otel.ports", "hexastack_otel.adapters", "hexastack_otel.infra"
        )
        .check("hexastack_otel")
    )


def test_ports_boundary_rules():
    (
        archrule("Ports layer must not import from forbidden layers")
        .match("hexastack_otel.ports")
        .should_not_import("hexastack_otel.adapters", "hexastack_otel.infra")
        .check("hexastack_otel")
    )
