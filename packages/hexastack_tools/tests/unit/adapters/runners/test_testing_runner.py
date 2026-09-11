"""Unit tests for SubprocessTestingRunnerAdapter.

Notes/Architectural Intent:
    Verifies that SubprocessTestingRunnerAdapter handles missing databases gracefully,
    executes subprocess commands, and parses sqlite coverage and mutmut records.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.adapters.runners.testing_runner import (
    SubprocessTestingRunnerAdapter,
)


def test_run_mutmut(tmp_path: Path):
    """Verify run_mutmut invokes subprocess with correct working directory."""
    adapter = SubprocessTestingRunnerAdapter()
    cache_file = tmp_path / ".mutmut-cache"
    cache_file.write_text("old cache")

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        code = adapter.run_mutmut(tmp_path, reset_cache=True)
        assert code == 0
        assert not cache_file.exists()
        mock_run.assert_called_once_with(["mutmut", "run"], cwd=tmp_path)


def test_read_mutmut_cache_missing_file(tmp_path: Path):
    """Verify missing mutmut cache returns empty list."""
    adapter = SubprocessTestingRunnerAdapter()
    records = adapter.read_mutmut_cache(tmp_path / "nonexistent.db")
    assert records == []


def test_read_mutmut_cache_with_sqlite(tmp_path: Path):
    """Verify querying SQLite mutmut cache."""
    db_file = tmp_path / ".mutmut-cache"
    con = sqlite3.connect(db_file)
    con.execute("CREATE TABLE SourceFile (id INTEGER PRIMARY KEY, filename TEXT)")
    con.execute(
        "CREATE TABLE Line (id INTEGER PRIMARY KEY, sourcefile INTEGER, line TEXT)"
    )
    con.execute(
        "CREATE TABLE Mutant (id INTEGER PRIMARY KEY, line INTEGER, status TEXT)"
    )
    con.execute("INSERT INTO SourceFile VALUES (1, 'packages/core/src/mod.py')")
    con.execute("INSERT INTO Line VALUES (1, 1, 'x = 1')")
    con.execute("INSERT INTO Mutant VALUES (10, 1, 'bad_survived')")
    con.commit()
    con.close()

    adapter = SubprocessTestingRunnerAdapter()
    records = adapter.read_mutmut_cache(db_file, package_filter="core")
    assert len(records) == 1
    assert records[0]["id"] == "10"
    assert records[0]["status"] == "bad_survived"


def test_get_changed_lines(tmp_path: Path):
    """Verify get_changed_lines runs git diff and parses output."""
    adapter = SubprocessTestingRunnerAdapter()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout="+++ b/packages/core/src/mod.py\n@@ -5 +5 @@\n+x = 2\n"
        )
        res = adapter.get_changed_lines(tmp_path)
        expected_path = (tmp_path / "packages/core/src/mod.py").resolve()
        assert expected_path in res
        assert 5 in res[expected_path]


def test_audit_missing_coverage(tmp_path: Path):
    """Verify audit methods return empty when coverage file does not exist."""
    adapter = SubprocessTestingRunnerAdapter()
    cov_path = tmp_path / "missing.coverage"
    assert adapter.find_impacted_tests({}, cov_path) == set()
    assert adapter.get_tests_covering_line("foo.py", 1, cov_path) == []
    assert adapter.audit_layer_boundary_leaks(cov_path) == []
    assert adapter.audit_redundant_tests(cov_path) == []


def test_execute_pytest(tmp_path: Path):
    """Verify execute_pytest invokes subprocess."""
    adapter = SubprocessTestingRunnerAdapter()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        res = adapter.execute_pytest(
            ["test_a.py::test_1"], extra_args=["-v"], cwd=tmp_path
        )
        assert res == 0
        mock_run.assert_called_once_with(
            ["pytest", "test_a.py::test_1", "-v"], cwd=tmp_path
        )
