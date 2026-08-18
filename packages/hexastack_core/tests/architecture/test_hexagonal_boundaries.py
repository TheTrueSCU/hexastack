"""Hexagonal architecture boundary tests for hexastack_core."""

from pytest_archon import archrule


def test_adapters_boundary_rules():
    (
        archrule("Adapters layer must not import from forbidden layers")
        .match("hexastack_core.adapters")
        .should_not_import("hexastack_core.testing")
        .check("hexastack_core")
    )


def test_domain_boundary_rules():
    (
        archrule("Domain layer must not import from forbidden layers")
        .match("hexastack_core.domain")
        .should_not_import(
            "hexastack_core.ports",
            "hexastack_core.adapters",
            "hexastack_core.infra",
            "hexastack_core.testing",
        )
        .check("hexastack_core")
    )


def test_infra_boundary_rules():
    (
        archrule("Infra layer must not import from forbidden layers")
        .match("hexastack_core.infra")
        .should_not_import("hexastack_core.testing")
        .check("hexastack_core")
    )


def test_ports_boundary_rules():
    (
        archrule("Ports layer must not import from forbidden layers")
        .match("hexastack_core.ports")
        .should_not_import(
            "hexastack_core.adapters", "hexastack_core.infra", "hexastack_core.testing"
        )
        .check("hexastack_core")
    )


def test_utils_boundary_rules():
    (
        archrule("Utils layer must not import from forbidden layers")
        .match("hexastack_core.utils")
        .should_not_import(
            "hexastack_core.domain",
            "hexastack_core.ports",
            "hexastack_core.adapters",
            "hexastack_core.infra",
            "hexastack_core.testing",
        )
        .check("hexastack_core")
    )
