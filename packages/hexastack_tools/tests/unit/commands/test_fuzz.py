"""Unit tests for coverage-guided and OWASP security fuzz command runner."""

from unittest.mock import MagicMock, patch

import pytest

from hexastack_tools.commands.fuzz import (
    display_fuzz_results,
    main,
    run_target_fuzz,
)


def test_fuzz_callables_exist():
    """Verify fuzz-run entrypoints are callable."""
    assert callable(main)
    assert callable(run_target_fuzz)
    assert callable(display_fuzz_results)


def test_display_fuzz_results_passing():
    """Verify display_fuzz_results returns 0 when all targets pass."""
    results = [
        {
            "target": "LogSanitizer",
            "engine": "standalone",
            "runs": 100,
            "duration_seconds": 0.05,
            "crashes": 0,
            "redos_violations": 0,
            "passed": True,
        },
        {
            "target": "ProtoCompiler",
            "engine": "standalone",
            "runs": 50,
            "duration_seconds": 0.02,
            "crashes": 0,
            "redos_violations": 0,
            "passed": True,
        },
    ]
    exit_code = display_fuzz_results(results)
    assert exit_code == 0


def test_display_fuzz_results_failing():
    """Verify display_fuzz_results returns 1 when a target has crashes or violations."""
    results = [
        {
            "target": "LogSanitizer",
            "engine": "standalone",
            "runs": 100,
            "duration_seconds": 0.05,
            "crashes": 1,
            "redos_violations": 0,
            "passed": False,
        },
    ]
    exit_code = display_fuzz_results(results)
    assert exit_code == 1


def test_run_target_fuzz_sanitizer():
    """Verify run_target_fuzz executes sanitizer target."""
    mock_mod = MagicMock()
    mock_mod.run_standalone.return_value = {
        "target": "LogSanitizer",
        "engine": "standalone",
        "runs": 10,
        "duration_seconds": 0.01,
        "crashes": 0,
        "redos_violations": 0,
        "passed": True,
    }
    with patch("importlib.import_module", return_value=mock_mod):
        res = run_target_fuzz(target="sanitizer", runs=10, engine="standalone")
        assert len(res) == 1
        assert res[0]["target"] == "LogSanitizer"
        mock_mod.run_standalone.assert_called_once_with(runs=10)


def test_run_target_fuzz_proto():
    """Verify run_target_fuzz executes proto target."""
    mock_mod = MagicMock()
    mock_mod.run_standalone.return_value = {
        "target": "ProtoCompiler",
        "engine": "standalone",
        "runs": 10,
        "duration_seconds": 0.01,
        "crashes": 0,
        "passed": True,
    }
    with patch("importlib.import_module", return_value=mock_mod):
        res = run_target_fuzz(target="proto", runs=10, engine="standalone")
        assert len(res) == 1
        assert res[0]["target"] == "ProtoCompiler"
        mock_mod.run_standalone.assert_called_once_with(runs=10)


def test_run_target_fuzz_owasp():
    """Verify run_target_fuzz executes OWASP target via pytest subprocess."""
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "4 passed in 2.0s"
        mock_run.return_value = mock_proc

        res = run_target_fuzz(target="owasp", runs=10)
        assert len(res) == 1
        assert res[0]["target"] == "OWASP Security Fuzz"
        assert res[0]["passed"] is True


def test_run_target_fuzz_unknown_target():
    """Verify run_target_fuzz raises ValueError for unrecognized target."""
    with pytest.raises(ValueError, match="Unknown fuzz target"):
        run_target_fuzz(target="invalid_target")


def test_main_cli_success():
    """Verify main() parses arguments and invokes runner."""
    with (
        patch(
            "sys.argv",
            [
                "fuzz-run",
                "--target",
                "sanitizer",
                "--runs",
                "10",
                "--engine",
                "standalone",
            ],
        ),
        patch("hexastack_tools.commands.fuzz.run_target_fuzz") as mock_run,
        patch("hexastack_tools.commands.fuzz.display_fuzz_results") as mock_display,
    ):
        mock_run.return_value = [{"passed": True, "crashes": 0, "redos_violations": 0}]
        mock_display.return_value = 0

        exit_code = main()
        assert exit_code == 0
        mock_run.assert_called_once_with(
            target="sanitizer", runs=10, engine="standalone"
        )


def test_main_cli_error_handling():
    """Verify main() handles exceptions gracefully and returns 1."""
    with (
        patch("sys.argv", ["fuzz-run", "--target", "all"]),
        patch(
            "hexastack_tools.commands.fuzz.run_target_fuzz",
            side_effect=ValueError("boom"),
        ),
    ):
        exit_code = main()
        assert exit_code == 1
