"""Hexagonal architecture boundary tests for hexastack_events."""

from pytest_archon import archrule


def test_domain_boundary_rules():
    (
        archrule("Domain layer must not import from forbidden layers")
        .match("hexastack_events.domain")
        .should_not_import(
            "hexastack_events.ports",
            "hexastack_events.adapters",
            "hexastack_events.infra",
        )
        .check("hexastack_events")
    )


def test_ports_boundary_rules():
    (
        archrule("Ports layer must not import from forbidden layers")
        .match("hexastack_events.ports")
        .should_not_import("hexastack_events.adapters", "hexastack_events.infra")
        .check("hexastack_events")
    )
