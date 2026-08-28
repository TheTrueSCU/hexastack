"""Unit tests for scaffolding tests templates."""

from hexastack.application.scaffolding.templates import tests


def test_tests_template_module_exports():
    assert tests is not None
