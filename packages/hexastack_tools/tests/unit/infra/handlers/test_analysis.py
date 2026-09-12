"""Unit tests for analysis CQRS command handlers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.domain.analysis import (
    FuzzRunCommand,
    ScanCodeQlCommand,
    UpdateInlineSnapshotsCommand,
)
from hexastack_tools.infra.handlers.analysis import (
    FuzzRunHandler,
    ScanCodeQlHandler,
    UpdateInlineSnapshotsHandler,
)


def test_scan_codeql_handler_cli_not_found(tmp_path: Path) -> None:
    """Verify ScanCodeQlHandler handles missing codeql CLI gracefully."""
    handler = ScanCodeQlHandler(root=tmp_path)
    with (
        patch("shutil.which", return_value=None),
        patch("pathlib.Path.is_file", return_value=False),
    ):
        report = handler.handle(ScanCodeQlCommand())
        assert report.is_successful is True
        assert "not found" in (report.error_message or "")


def test_scan_codeql_handler_success(tmp_path: Path) -> None:
    """Verify ScanCodeQlHandler executes database creation and analysis."""
    handler = ScanCodeQlHandler(root=tmp_path)
    sarif_data = {
        "runs": [
            {
                "results": [
                    {"level": "warning", "message": {"text": "warn"}},
                    {"level": "error", "message": {"text": "err"}},
                ]
            }
        ]
    }
    sarif_file = tmp_path / "out.sarif"
    sarif_file.write_text(json.dumps(sarif_data), encoding="utf-8")

    mock_run = MagicMock()
    mock_run.returncode = 0
    mock_run.stderr = ""

    with (
        patch("shutil.which", return_value="/bin/codeql"),
        patch("subprocess.run", return_value=mock_run),
    ):
        report = handler.handle(ScanCodeQlCommand(output_sarif=sarif_file))
        assert report.is_successful is True
        assert report.findings_count == 2
        assert report.critical_count == 1


def test_fuzz_run_handler(tmp_path: Path) -> None:
    """Verify FuzzRunHandler delegates to fuzz harness runner and aggregates results."""
    handler = FuzzRunHandler(root=tmp_path)
    mock_metrics = [
        {
            "target": "sanitizer",
            "engine": "atheris",
            "runs": 100,
            "duration_seconds": 0.5,
            "crashes": 0,
            "redos_violations": 0,
            "passed": True,
        }
    ]
    with patch(
        "hexastack_tools.commands.fuzz.run_target_fuzz", return_value=mock_metrics
    ):
        report = handler.handle(FuzzRunCommand(target="sanitizer", runs=100))
        assert report.all_passed is True
        assert len(report.results) == 1
        assert report.results[0].target == "sanitizer"


def test_update_inline_snapshots_handler(tmp_path: Path) -> None:
    """Verify UpdateInlineSnapshotsHandler invokes snapshot runner."""
    target = tmp_path / "packages" / "core"
    target.mkdir(parents=True)
    handler = UpdateInlineSnapshotsHandler(root=tmp_path)

    with patch(
        "hexastack_tools.commands.inline_snapshot.run_snapshot_update_for_dir",
        return_value=0,
    ):
        report = handler.handle(
            UpdateInlineSnapshotsCommand(mode="fix", targets=(target,))
        )
        assert report.exit_code == 0
        assert len(report.targets_updated) == 1
