"""Unit tests for scaffolding ci templates."""

from hexastack.application.scaffolding.templates import ci


def test_ci_template_module_exports():
    assert ci is not None
