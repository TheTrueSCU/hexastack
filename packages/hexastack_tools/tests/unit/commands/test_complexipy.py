"""Unit tests for filtered complexipy command runner."""

from unittest.mock import MagicMock, patch

from hexastack_tools.commands.complexipy import main, run_complexipy


def test_complexipy_callables_exist():
    """Verify complexipy entrypoints are callable."""
    assert callable(main)
    assert callable(run_complexipy)


def test_run_complexipy_passes():
    """Verify run_complexipy returns 0 when no functions exceed threshold."""
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.stdout = "packages/pkg/a.py func_a 10\npackages/pkg/b.py func_b 15\n"
        mock_run.return_value = mock_proc

        result = run_complexipy(["packages"], max_complexity=25)
        assert result == 0


def test_run_complexipy_fails_on_violation():
    """Verify run_complexipy returns 1 and reports violating functions."""
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.stdout = "packages/pkg/a.py func_a 10\npackages/pkg/b.py func_b 28\n"
        mock_run.return_value = mock_proc

        result = run_complexipy(["packages"], max_complexity=25)
        assert result == 1
