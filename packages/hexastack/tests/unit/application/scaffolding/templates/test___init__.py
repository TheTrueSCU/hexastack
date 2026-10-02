"""Unit tests for scaffolding templates root module."""

from hexastack.application.scaffolding import templates


def test_templates_root_exports():
    assert hasattr(templates, "render_pyproject_toml")
    assert hasattr(templates, "render_dockerfile")
    assert hasattr(templates, "render_github_ci")
