"""Unit tests for Hexastack project scaffolding generator."""

import tempfile
from pathlib import Path

import pytest

from hexastack.application.scaffolding.generator import (
    ProjectScaffolder,
    ScaffoldConfig,
    scaffold_project,
)


def test_scaffold_project_generates_all_files():
    """Verify scaffolder generates valid hexagonal architecture layout."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_dir = Path(tmpdir)
        proj_dir = scaffold_project(
            name="order-service",
            template="web-api",
            description="Test order microservice",
            output_dir=dest_dir,
        )

        assert proj_dir.exists()
        assert (proj_dir / "pyproject.toml").exists()
        assert (proj_dir / ".importlinter").exists()
        assert (proj_dir / ".pre-commit-config.yaml").exists()
        assert (proj_dir / ".github" / "workflows" / "ci.yml").exists()
        assert (proj_dir / "README.md").exists()

        # Check source layout
        src_dir = proj_dir / "src" / "order_service"
        assert (src_dir / "domain" / "models.py").exists()
        assert (src_dir / "domain" / "commands.py").exists()
        assert (src_dir / "ports" / "repositories.py").exists()
        assert (src_dir / "adapters" / "driven" / "database.py").exists()
        assert (src_dir / "adapters" / "driving" / "http.py").exists()
        assert (src_dir / "adapters" / "driving" / "cli.py").exists()
        assert (src_dir / "infra" / "bootstrap.py").exists()
        assert (src_dir / "infra" / "config.py").exists()

        # Check tests layout
        tests_dir = proj_dir / "tests"
        assert (tests_dir / "conftest.py").exists()
        assert (tests_dir / "unit" / "test_domain.py").exists()
        assert (tests_dir / "hypothesis" / "test_domain_fuzz.py").exists()


def test_scaffold_project_raises_if_directory_exists():
    """Verify scaffolder raises FileExistsError if directory already populated."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_dir = Path(tmpdir)
        proj_dir = dest_dir / "existing-service"
        proj_dir.mkdir()
        (proj_dir / "existing.txt").write_text("hello")

        config = ScaffoldConfig(name="existing-service")
        scaffolder = ProjectScaffolder(config, output_dir=dest_dir)

        with pytest.raises(FileExistsError, match="already exists and is not empty"):
            scaffolder.generate()
