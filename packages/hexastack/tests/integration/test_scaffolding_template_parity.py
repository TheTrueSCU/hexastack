"""Integration tests verifying scaffolding output matches template standards and passes checks."""

from __future__ import annotations

import py_compile
import tempfile
from pathlib import Path

from hexastack.application.scaffolding.generator import scaffold_project


def test_golden_path_web_api_parity() -> None:
    """Verify web-api scaffold generates golden-path structure and valid python syntax.

    Notes/Architectural Intent:
        Guarantees that downstream starter repositories like `TheTrueSCU/hexastack-template`
        remain in lockstep with the generator output, preventing drift in dependencies,
        baseline security files, and python source syntax.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_dir = Path(tmpdir)
        proj_dir = scaffold_project(
            name="golden-service",
            template="web-api",
            description="Golden path reference service",
            output_dir=dest_dir,
        )

        project_exists = proj_dir.exists()
        assert project_exists is True

        # 1. Structural file integrity
        expected_files = [
            "pyproject.toml",
            ".gitignore",
            ".secrets.baseline",
            ".pre-commit-config.yaml",
            ".importlinter",
            ".github/workflows/ci.yml",
            "README.md",
            "Dockerfile",
            ".dockerignore",
            ".devcontainer/devcontainer.json",
            "AGENTS.md",
            "GEMINI.md",
            "src/golden_service/__init__.py",
            "src/golden_service/domain/__init__.py",
            "src/golden_service/domain/models.py",
            "src/golden_service/domain/commands.py",
            "src/golden_service/ports/__init__.py",
            "src/golden_service/ports/repositories.py",
            "src/golden_service/adapters/__init__.py",
            "src/golden_service/adapters/driven/__init__.py",
            "src/golden_service/adapters/driven/database.py",
            "src/golden_service/adapters/driving/__init__.py",
            "src/golden_service/adapters/driving/cli.py",
            "src/golden_service/adapters/driving/http.py",
            "src/golden_service/infra/__init__.py",
            "src/golden_service/infra/bootstrap.py",
            "src/golden_service/infra/config.py",
            "src/golden_service/infra/handlers.py",
            "tests/__init__.py",
            "tests/conftest.py",
            "tests/architecture/__init__.py",
            "tests/architecture/test_hexagonal_boundaries.py",
            "tests/hypothesis/__init__.py",
            "tests/hypothesis/test_domain_fuzz.py",
            "tests/unit/__init__.py",
            "tests/unit/domain/__init__.py",
            "tests/unit/domain/test_models.py",
            "tests/unit/ports/__init__.py",
            "tests/unit/ports/test_repositories.py",
            "tests/unit/adapters/__init__.py",
            "tests/unit/adapters/driven/__init__.py",
            "tests/unit/adapters/driven/test_database.py",
            "tests/unit/adapters/driving/__init__.py",
            "tests/unit/adapters/driving/test_cli.py",
            "tests/unit/adapters/driving/test_http.py",
            "tests/unit/infra/__init__.py",
            "tests/unit/infra/test_bootstrap.py",
            "tests/unit/infra/test_config.py",
            "tests/unit/infra/test_handlers.py",
        ]

        for rel_path in expected_files:
            target = proj_dir / rel_path
            target_exists = target.exists()
            assert target_exists is True

        # 2. Pyproject dependencies & settings check
        pyproject_content = (proj_dir / "pyproject.toml").read_text(encoding="utf-8")
        has_pydantic_settings = "pydantic-settings>=2.0.0" in pyproject_content
        assert has_pydantic_settings is True
        has_cli_extra = "cli" in pyproject_content
        assert has_cli_extra is True
        has_per_file_ignores = "[tool.ruff.lint.per-file-ignores]" in pyproject_content
        assert has_per_file_ignores is True

        # 3. Gitignore hygiene
        gitignore_content = (proj_dir / ".gitignore").read_text(encoding="utf-8")
        ignores_git = "\n.git\n" in gitignore_content
        assert ignores_git is False
        ignores_gitignore = "\n.gitignore\n" in gitignore_content
        assert ignores_gitignore is False
        ignores_baseline = "\n.secrets.baseline\n" in gitignore_content
        assert ignores_baseline is False
        has_agent_rules_ignore = ".agents/rules/hexaqual-*" in gitignore_content
        assert has_agent_rules_ignore is True

        # 4. CI workflow flags
        ci_content = (proj_dir / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        has_sync_args = 'sync-args: "--all-groups"' in ci_content
        assert has_sync_args is True
        has_all_groups_install = "uv sync --all-groups" in ci_content
        assert has_all_groups_install is True

        # 5. Clean Python byte-compilation of all generated python files
        python_files = list(proj_dir.rglob("*.py"))
        py_files_count = len(python_files)
        has_python_files = py_files_count > 0
        assert has_python_files is True

        for py_file in python_files:
            compiled = py_compile.compile(str(py_file), doraise=True)
            assert compiled is not None
