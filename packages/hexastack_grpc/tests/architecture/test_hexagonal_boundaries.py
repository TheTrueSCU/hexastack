"""Hexagonal architecture boundary tests for hexastack_grpc."""

from pytest_archon import archrule


def test_domain_boundary_rules():
    (
        archrule("Domain layer must not import from forbidden layers")
        .match("hexastack_grpc.domain")
        .should_not_import("hexastack_grpc.adapters", "hexastack_grpc.infra")
        .check("hexastack_grpc")
    )
