"""Unit tests for extras parity utilities.

Notes/Architectural Intent:
    Verifies audit_extras_parity detection of missing forwarded extras
    and Mermaid diagram rendering.
"""

from pathlib import Path

from hexastack_tools.utils.extras_parity import (
    audit_extras_parity,
    generate_extras_mermaid_diagram,
)


def test_audit_extras_parity_missing_umbrella_toml(tmp_path: Path):
    """Verify handling when umbrella pyproject.toml is missing."""
    violations = audit_extras_parity(tmp_path)
    assert len(violations) == 1
    assert violations[0].extra_name == "<root>"


def test_audit_extras_parity_and_diagram_generation(tmp_path: Path):
    """Verify auditing and Mermaid generation with configured workspace."""
    umbrella_dir = tmp_path / "packages" / "hexastack"
    umbrella_dir.mkdir(parents=True)
    (umbrella_dir / "pyproject.toml").write_text(
        """
[project]
name = "hexastack"

[project.optional-dependencies]
sqlite = ["hexastack-db[sqlite]"]
all = ["hexastack-db[sqlite]"]
""",
        encoding="utf-8",
    )

    db_dir = tmp_path / "packages" / "hexastack_db"
    db_dir.mkdir(parents=True)
    (db_dir / "pyproject.toml").write_text(
        """
[project]
name = "hexastack-db"

[project.optional-dependencies]
sqlite = ["aiosqlite>=0.20"]
unforwarded = ["some-pkg>=1.0"]
""",
        encoding="utf-8",
    )

    violations = audit_extras_parity(tmp_path)
    assert len(violations) == 1
    assert violations[0].subpackage == "hexastack-db"
    assert violations[0].extra_name == "unforwarded"

    diagram = generate_extras_mermaid_diagram(tmp_path)
    assert "graph LR" in diagram
    assert "hexastack (Umbrella Package)" in diagram
