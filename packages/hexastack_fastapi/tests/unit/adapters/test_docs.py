"""Unit tests for Zensical documentation mounting adapter."""

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from hexastack_fastapi.adapters.docs import mount_zensical_docs
from hexastack_fastapi.domain.config import (
    HexastackFastApiConfig,
    ZensicalDocsConfig,
)
from hexastack_fastapi.infra.app import create_fastapi_app


def test_mount_zensical_docs_explicit_helper():
    """Verify mounting Zensical docs using the helper function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_dir = Path(tmpdir) / "site"
        doc_dir.mkdir()
        (doc_dir / "index.html").write_text(
            "<html><body><h1>Hexastack Docs</h1></body></html>", encoding="utf-8"
        )
        (doc_dir / "guide.html").write_text(
            "<html><body><h1>Guide Page</h1></body></html>", encoding="utf-8"
        )

        app = create_fastapi_app()
        mount_zensical_docs(app=app, path="/guide", site_dir=doc_dir)

        client = TestClient(app)

        # 1. Verify OpenAPI Swagger UI is preserved at /docs
        resp_openapi = client.get("/docs")
        assert resp_openapi.status_code == 200

        # 2. Verify Zensical docs are served at /guide
        resp_guide_index = client.get("/guide/")
        assert resp_guide_index.status_code == 200
        assert "Hexastack Docs" in resp_guide_index.text

        # 3. Verify subpage
        resp_guide_subpage = client.get("/guide/guide.html")
        assert resp_guide_subpage.status_code == 200
        assert "Guide Page" in resp_guide_subpage.text


def test_mount_zensical_docs_via_configuration():
    """Verify mounting Zensical docs via HexastackFastApiConfig knobs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        doc_dir = Path(tmpdir) / "custom_site"
        doc_dir.mkdir()
        (doc_dir / "index.html").write_text(
            "<html><body><h1>Configured Zensical</h1></body></html>", encoding="utf-8"
        )

        cfg = HexastackFastApiConfig(
            docs_url="/api-docs",  # Custom OpenAPI path
            zensical=ZensicalDocsConfig(
                enable=True,
                path="/developer-guide",
                site_dir=str(doc_dir),
            ),
        )
        app = create_fastapi_app(config=cfg)
        client = TestClient(app)

        # OpenAPI at custom path
        assert client.get("/api-docs").status_code == 200

        # Zensical docs at configured path
        resp = client.get("/developer-guide/")
        assert resp.status_code == 200
        assert "Configured Zensical" in resp.text


def test_mount_zensical_docs_production_missing_dir_raises(monkeypatch):
    """Verify DocumentationNotFoundError raised when site_dir is missing in production."""
    import pytest

    from hexastack_fastapi.adapters.docs import DocumentationNotFoundError

    monkeypatch.setenv("ENVIRONMENT", "production")
    app = create_fastapi_app()

    with pytest.raises(DocumentationNotFoundError):
        mount_zensical_docs(app=app, path="/guide", site_dir="/non/existent/path/xyz")


def test_mount_zensical_docs_development_missing_dir_creates_placeholder(
    monkeypatch, tmp_path
):
    """Verify development mode gracefully creates placeholder index.html if missing."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    missing_dir = tmp_path / "missing_site_dir"

    app = create_fastapi_app()
    mount_zensical_docs(app=app, path="/guide", site_dir=missing_dir)

    client = TestClient(app)
    resp = client.get("/guide/")
    assert resp.status_code == 200
    assert "Documentation building..." in resp.text
