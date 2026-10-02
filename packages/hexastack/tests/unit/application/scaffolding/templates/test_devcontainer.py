"""Unit tests for devcontainer scaffolding template.

Notes/Architectural Intent:
    Ensures that generated `.devcontainer/devcontainer.json` files are syntactically
    valid JSON, configure required devcontainer features and extensions, and properly
    adapt the `postCreateCommand` based on project configuration options.
"""

from __future__ import annotations

import json

from hexastack.application.scaffolding.models import ScaffoldConfig
from hexastack.application.scaffolding.templates.devcontainer import (
    render_devcontainer_json,
)


def test_render_devcontainer_json_valid_and_complete():
    """Verify rendered devcontainer configuration is valid JSON with expected properties."""
    config = ScaffoldConfig(
        name="test-service",
        template="microservice",
        include_qual=True,
    )

    rendered = render_devcontainer_json(config)
    parsed = json.loads(rendered)

    name_field = parsed.get("name")
    assert name_field == "test-service Dev Container"

    image_field = parsed.get("image")
    assert "3.13" in image_field

    ports = parsed.get("forwardPorts")
    assert 8000 in ports
    assert 8080 in ports

    post_create = parsed.get("postCreateCommand")
    assert "hexaqual hooks install" in post_create


def test_render_devcontainer_json_without_qual():
    """Verify postCreateCommand is simplified when Hexaqual governance is disabled."""
    config = ScaffoldConfig(
        name="lean-service",
        template="microservice",
        include_qual=False,
    )

    rendered = render_devcontainer_json(config)
    parsed = json.loads(rendered)

    post_create = parsed.get("postCreateCommand")
    assert post_create == "uv sync --all-extras"
