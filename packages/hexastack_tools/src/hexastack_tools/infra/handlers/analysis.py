"""CQRS command handlers for security scanning, fuzzing, and inline snapshot updates.

Notes/Architectural Intent:
    Orchestrates execution of local CodeQL security scanning, Atheris/OWASP
    fuzzing harnesses, and inline snapshot updates, returning immutable domain reports.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from hexastack_tools.domain.analysis import (
    CodeQlScanReport,
    FuzzRunCommand,
    FuzzRunReport,
    FuzzTargetResult,
    InlineSnapshotsReport,
    ScanCodeQlCommand,
    UpdateInlineSnapshotsCommand,
)
from hexastack_tools.utils.workspace import get_repo_root


class ScanCodeQlHandler:
    """Handler executing local CodeQL SAST security analysis."""

    def __init__(self, root: Path | None = None) -> None:
        """Initialize ScanCodeQlHandler with monorepo root.

        Args:
            root: Root path of monorepo workspace.
        """
        self._root = root or get_repo_root()

    def handle(self, command: ScanCodeQlCommand) -> CodeQlScanReport:
        """Execute CodeQL database creation and analysis.

        Args:
            command: ScanCodeQlCommand with query suite and output options.

        Returns:
            CodeQlScanReport containing findings count and SARIF path.

        Notes/Architectural Intent:
            Checks for codeql CLI availability, creates an isolated temporary
            database, evaluates query suites, and parses SARIF results.
        """
        bundle_bin = Path.home() / ".local/share/codeql/codeql"
        codeql_bin = str(bundle_bin) if bundle_bin.is_file() else shutil.which("codeql")
        if not codeql_bin:
            return CodeQlScanReport(
                is_successful=True,
                error_message="CodeQL CLI not found in system PATH or ~/.local/share/codeql. Skipping.",
            )

        with tempfile.TemporaryDirectory(prefix="hexastack-codeql-db-") as tmp_db_dir:
            db_path = Path(tmp_db_dir) / "db"
            sarif_file = command.output_sarif or (Path(tmp_db_dir) / "results.sarif")

            create_cmd = [
                codeql_bin,
                "database",
                "create",
                str(db_path),
                "--language=python",
                f"--source-root={self._root}",
                "--overwrite",
            ]
            if command.threads > 0:
                create_cmd.append(f"--threads={command.threads}")

            res = subprocess.run(
                create_cmd, cwd=self._root, capture_output=True, text=True, check=False
            )
            if res.returncode != 0:
                return CodeQlScanReport(
                    is_successful=False,
                    error_message=f"CodeQL database creation failed:\n{res.stderr}",
                )

            analyze_cmd = [
                codeql_bin,
                "database",
                "analyze",
                str(db_path),
                command.query_suite,
                "--format=sarif-latest",
                f"--output={sarif_file}",
            ]
            if command.threads > 0:
                analyze_cmd.append(f"--threads={command.threads}")

            res = subprocess.run(
                analyze_cmd, cwd=self._root, capture_output=True, text=True, check=False
            )
            if res.returncode != 0:
                return CodeQlScanReport(
                    is_successful=False,
                    error_message=f"CodeQL query execution failed:\n{res.stderr}",
                )

            total_findings = 0
            critical_findings = 0
            if sarif_file.is_file():
                try:
                    data = json.loads(sarif_file.read_text(encoding="utf-8"))
                    runs = data.get("runs", [])
                    for run in runs:
                        results = run.get("results", [])
                        total_findings += len(results)
                        for r in results:
                            level = r.get("level", "warning")
                            if level in ("error", "critical"):
                                critical_findings += 1
                except Exception:
                    pass

            return CodeQlScanReport(
                sarif_path=sarif_file,
                findings_count=total_findings,
                critical_count=critical_findings,
                is_successful=True,
            )


class FuzzRunHandler:
    """Handler executing Atheris and OWASP security fuzzing harnesses."""

    def __init__(self, root: Path | None = None) -> None:
        """Initialize FuzzRunHandler."""
        self._root = root or get_repo_root()

    def handle(self, command: FuzzRunCommand) -> FuzzRunReport:
        """Execute selected fuzzing targets.

        Args:
            command: FuzzRunCommand specifying target and iterations.

        Returns:
            FuzzRunReport aggregating results across all targets.

        Notes/Architectural Intent:
            Delegates execution to harness runners and standardizes metrics.
        """
        from hexastack_tools.commands.fuzz import run_target_fuzz

        raw_results = run_target_fuzz(
            target=command.target,
            runs=command.runs,
            engine=command.engine,
        )

        results: list[FuzzTargetResult] = []
        for r in raw_results:
            results.append(
                FuzzTargetResult(
                    target=str(r.get("target", "unknown")),
                    engine=str(r.get("engine", "unknown")),
                    runs=int(r.get("runs", 0)),
                    duration_seconds=float(r.get("duration_seconds", 0.0)),
                    crashes=int(r.get("crashes", 0)),
                    redos_violations=int(r.get("redos_violations", 0)),
                    passed=bool(r.get("passed", False)),
                )
            )

        all_ok = all(r.passed for r in results) if results else True
        return FuzzRunReport(results=tuple(results), all_passed=all_ok)


class UpdateInlineSnapshotsHandler:
    """Handler synchronizing inline snapshots across packages."""

    def __init__(self, root: Path | None = None) -> None:
        """Initialize UpdateInlineSnapshotsHandler."""
        self._root = root or get_repo_root()

    def handle(self, command: UpdateInlineSnapshotsCommand) -> InlineSnapshotsReport:
        """Execute inline snapshot updates.

        Args:
            command: UpdateInlineSnapshotsCommand with mode and targets.

        Returns:
            InlineSnapshotsReport with processed paths and exit code.

        Notes/Architectural Intent:
            Runs pytest in single-process mode with --inline-snapshot flags.
        """
        from hexastack_tools.commands.inline_snapshot import run_snapshot_update_for_dir
        from hexastack_tools.utils.workspace import get_package_directories

        targets = (
            list(command.targets)
            if command.targets
            else get_package_directories(self._root)
        )

        exit_code = 0
        updated: list[str] = []
        for target in targets:
            code = run_snapshot_update_for_dir(target, command.mode)
            updated.append(
                str(
                    target.relative_to(self._root)
                    if target.is_relative_to(self._root)
                    else target
                )
            )
            if code != 0:
                exit_code = code

        return InlineSnapshotsReport(
            targets_updated=tuple(updated),
            exit_code=exit_code,
        )


__all__ = [
    "FuzzRunHandler",
    "ScanCodeQlHandler",
    "UpdateInlineSnapshotsHandler",
]
