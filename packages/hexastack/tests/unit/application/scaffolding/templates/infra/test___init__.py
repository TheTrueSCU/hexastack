"""Unit tests for scaffolding infra templates."""

from hexastack.application.scaffolding.templates import infra


def test_infra_template_module_exports():
    assert infra is not None
