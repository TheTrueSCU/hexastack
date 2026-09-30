"""Devcontainer configuration template for scaffolded projects.

Notes/Architectural Intent:
    Renders standardized `.devcontainer/devcontainer.json` specification
    supporting zero-install GitHub Codespaces and VS Code Dev Containers
    with Python 3.13, uv, Ruff, and automated port forwarding.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hexastack.application.scaffolding.models import ScaffoldConfig

__all__ = [
    "render_devcontainer_json",
]


def render_devcontainer_json(config: ScaffoldConfig) -> str:
    """Render a formatted devcontainer.json configuration for a project.

    Args:
        config: Scaffolding configuration.

    Returns:
        JSON-formatted devcontainer configuration string.

    Notes/Architectural Intent:
        Pre-wires Python 3.13, uv, and GitHub CLI devcontainer features,
        configures Ruff formatting on save, forwards standard HTTP (8000)
        and DevTools (8080) ports, and sets up postCreate commands.
    """
    post_create = (
        "uv sync --all-extras && uv run hexaqual hooks install"
        if config.include_qual
        else "uv sync --all-extras"
    )

    data: dict[str, Any] = {
        "name": f"{config.name} Dev Container",
        "image": "mcr.microsoft.com/devcontainers/python:3.13-bookworm",
        "features": {
            "ghcr.io/devcontainers/features/github-cli:1": {},
            "ghcr.io/devcontainers-extra/features/uv:1": {},
        },
        "customizations": {
            "vscode": {
                "extensions": [
                    "charliermarsh.ruff",
                    "ms-python.python",
                    "ms-python.vscode-pylance",
                    "tamasfe.even-better-toml",
                    "redhat.vscode-yaml",
                    "github.vscode-github-actions",
                ],
                "settings": {
                    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
                    "[python]": {
                        "editor.defaultFormatter": "charliermarsh.ruff",
                        "editor.formatOnSave": True,
                        "editor.codeActionsOnSave": {
                            "source.fixAll": "explicit",
                            "source.organizeImports": "explicit",
                        },
                    },
                    "python.testing.pytestEnabled": True,
                    "python.testing.pytestArgs": ["tests"],
                },
            }
        },
        "forwardPorts": [8000, 8080],
        "portsAttributes": {
            "8000": {
                "label": "FastAPI REST Server / API",
                "onAutoForward": "notify",
            },
            "8080": {
                "label": "NiceGUI DevTools Web UI",
                "onAutoForward": "notify",
            },
        },
        "postCreateCommand": post_create,
        "remoteUser": "vscode",
    }

    return json.dumps(data, indent=4) + "\n"
