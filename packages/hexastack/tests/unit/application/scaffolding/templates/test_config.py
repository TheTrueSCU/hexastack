"""Unit tests for scaffolding config templates."""

from hexastack.application.scaffolding.templates import config


def test_config_template_module_exports():
    assert config is not None
