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


def test_scaffold_mcp_agent_project():
    """Verify scaffolder generates mcp driving adapter and mcp.json config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_dir = Path(tmpdir)
        proj_dir = scaffold_project(
            name="agent-toolset",
            template="mcp-agent",
            description="Agent toolset microservice",
            output_dir=dest_dir,
        )

        assert proj_dir.exists()
        assert (proj_dir / "mcp.json").exists()
        assert "gemini" in (proj_dir / "mcp.json").read_text()

        src_dir = proj_dir / "src" / "agent_toolset"
        assert (src_dir / "adapters" / "driving" / "mcp.py").exists()
        assert "mcp_tool" in (src_dir / "adapters" / "driving" / "mcp.py").read_text()
        assert (
            "adapters.driving.mcp" in (src_dir / "infra" / "bootstrap.py").read_text()
        )


def test_scaffold_grpc_service():
    """Verify scaffolder generates gRPC service with @proto_schema inline contract."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_dir = Path(tmpdir)
        proj_dir = scaffold_project(
            name="rpc-service",
            template="grpc-service",
            output_dir=dest_dir,
        )
        src_dir = proj_dir / "src" / "rpc_service"
        assert (src_dir / "adapters" / "driving" / "grpc.py").exists()
        grpc_code = (src_dir / "adapters" / "driving" / "grpc.py").read_text()
        assert "@proto_schema" in grpc_code
        assert "package rpc_service.v1;" in grpc_code


def test_scaffold_graphql_service():
    """Verify scaffolder generates Strawberry GraphQL schema and resolvers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_dir = Path(tmpdir)
        proj_dir = scaffold_project(
            name="gql-service",
            template="graphql-service",
            output_dir=dest_dir,
        )
        src_dir = proj_dir / "src" / "gql_service"
        assert (src_dir / "adapters" / "driving" / "graphql.py").exists()
        gql_code = (src_dir / "adapters" / "driving" / "graphql.py").read_text()
        assert "@strawberry.type" in gql_code
        assert "@strawberry.mutation" in gql_code
        assert "schema = strawberry.Schema" in gql_code


def test_scaffold_with_release_and_openssf():
    """Verify scaffolder generates release workflow, changelog, and OpenSSF governance suite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_dir = Path(tmpdir)
        proj_dir = scaffold_project(
            name="secure-service",
            template="web-api",
            include_release=True,
            include_openssf=True,
            output_dir=dest_dir,
        )

        # Verify release assets
        assert (proj_dir / ".github" / "workflows" / "release.yml").exists()
        release_yml = (proj_dir / ".github" / "workflows" / "release.yml").read_text()
        assert "anchore/sbom-action" in release_yml
        assert "pypa/gh-action-pypi-publish" in release_yml
        assert (proj_dir / "CHANGELOG.md").exists()

        # Verify OpenSSF & Governance assets
        assert (proj_dir / ".github" / "workflows" / "scorecard.yml").exists()
        scorecard_yml = (
            proj_dir / ".github" / "workflows" / "scorecard.yml"
        ).read_text()
        assert "ossf/scorecard-action" in scorecard_yml
        assert (proj_dir / "SECURITY.md").exists()
        assert (proj_dir / "GOVERNANCE.md").exists()
        assert (proj_dir / "CODE_OF_CONDUCT.md").exists()


def test_scaffold_enterprise_includes_all_batteries():
    """Verify enterprise template enables release, openssf, events, mcp, grpc, and graphql."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_dir = Path(tmpdir)
        proj_dir = scaffold_project(
            name="mega-service",
            template="enterprise",
            include_release=True,
            include_openssf=True,
            output_dir=dest_dir,
        )

        assert (proj_dir / ".github" / "workflows" / "release.yml").exists()
        assert (proj_dir / ".github" / "workflows" / "scorecard.yml").exists()
        assert (proj_dir / "SECURITY.md").exists()
        assert (proj_dir / "CHANGELOG.md").exists()
        assert (
            proj_dir / "src" / "mega_service" / "adapters" / "driving" / "grpc.py"
        ).exists()
        assert (
            proj_dir / "src" / "mega_service" / "adapters" / "driving" / "graphql.py"
        ).exists()
        assert (
            proj_dir / "src" / "mega_service" / "adapters" / "driving" / "mcp.py"
        ).exists()
