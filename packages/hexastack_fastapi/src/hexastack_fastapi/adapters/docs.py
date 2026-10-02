"""Zensical and static documentation mounting adapter for FastAPI.

Notes/Architectural Intent:
    Provides a declarative helper to serve pre-built Zensical or static HTML documentation
    directly alongside FastAPI API routes:
    1. Supports configurable mount paths (e.g. `/guide`, `/docs-site`, `/handbook`) to avoid
       conflicts with FastAPI's native OpenAPI Swagger UI (`/docs`) and ReDoc (`/redoc`).
    2. Allows custom fallback and index.html serving with static directory validation.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from hexastack_core.domain.exceptions import HexastackError


class DocumentationNotFoundError(HexastackError):
    """Raised when configured documentation directory does not exist."""


def mount_zensical_docs(
    app: FastAPI,
    path: str = "/guide",
    site_dir: str | Path = "site",
    name: str = "zensical-docs",
    html: bool = True,
) -> None:
    """Mount a pre-built Zensical static documentation site onto a FastAPI application.

    Notes/Architectural Intent:
        FastAPI defaults OpenAPI Swagger UI to `/docs` and ReDoc to `/redoc`.
        Mounting Zensical under a configurable path (defaulting to `/guide`) enables
        teams to serve complete developer guides, architecture diagrams, and tutorials
        from the exact same microservice process without routing collisions.

    Args:
        app: Target FastAPI application.
        path: URL prefix where documentation will be served (e.g. "/guide" or "/manual").
        site_dir: Path to directory containing built HTML files (typically "site" from `zensical build`).
        name: Internal ASGI mount name.
        html: Enable HTML mode (auto-resolving directory paths to index.html).

    Raises:
        DocumentationNotFoundError: If site_dir does not exist and is required.
    """
    resolved_dir = Path(site_dir).resolve()

    if not resolved_dir.exists():
        if os.environ.get("ENVIRONMENT", "").lower() in ("prod", "production"):
            raise DocumentationNotFoundError(
                f"Zensical documentation directory '{resolved_dir}' not found. "
                f"Run 'zensical build' before launching the production server."
            )
        # In development/test mode, create the directory if missing to allow graceful startup
        resolved_dir.mkdir(parents=True, exist_ok=True)
        index_file = resolved_dir / "index.html"
        if not index_file.exists():
            index_file.write_text(
                "<!DOCTYPE html><html><body><h1>Documentation building...</h1>"
                "<p>Run <code>zensical build</code> to compile docs.</p></body></html>",
                encoding="utf-8",
            )

    normalized_path = "/" + path.strip("/")
    app.mount(
        normalized_path,
        StaticFiles(directory=str(resolved_dir), html=html),
        name=name,
    )


__all__ = [
    "DocumentationNotFoundError",
    "mount_zensical_docs",
]
