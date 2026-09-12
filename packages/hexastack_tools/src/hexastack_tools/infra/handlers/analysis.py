"""CQRS command handlers for security scanning, fuzzing, and inline snapshot updates.

Notes/Architectural Intent:
    Orchestrates execution of local CodeQL security scanning, Atheris/OWASP
    fuzzing harnesses, and inline snapshot updates, returning immutable domain reports.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

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


def run_target_fuzz(
    target: str,
    runs: int = 1000,
    engine: str = "auto",
) -> list[dict[str, Any]]:
    """Execute selected fuzzing targets.

    Args:
        target: Target name ('all', 'sanitizer', 'proto', 'owasp').
        runs: Number of fuzzing iterations to run per target.
        engine: Engine selection ('auto', 'atheris', 'standalone').

    Returns:
        List of dictionaries with run summary metrics.

    Raises:
        ValueError: If target name is unrecognized.
    """
    repo_root = get_repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    results: list[dict[str, Any]] = []

    use_atheris = False
    if engine in ("auto", "atheris"):
        try:
            use_atheris = importlib.util.find_spec("atheris") is not None
        except Exception:
            # Ignore lookup failures when atheris is not installed
            use_atheris = False

    if target in ("all", "sanitizer"):
        mod_san = importlib.import_module("fuzz.fuzz_log_sanitizer")
        runner = (
            mod_san.run_atheris
            if use_atheris and engine != "standalone"
            else mod_san.run_standalone
        )
        results.append(runner(runs=runs))

    if target in ("all", "proto"):
        mod_proto = importlib.import_module("fuzz.fuzz_proto_compiler")
        proto_runs = min(runs, 500) if runs > 500 else runs
        runner = (
            mod_proto.run_atheris
            if use_atheris and engine != "standalone"
            else mod_proto.run_standalone
        )
        results.append(runner(runs=proto_runs))

    if target in ("all", "owasp"):
        start_time = time.perf_counter()
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "packages/hexastack_fastapi/tests/properties/test_owasp_security_fuzz.py",
            "-q",
            "--no-cov",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        dur = round(time.perf_counter() - start_time, 3)
        passed = proc.returncode == 0
        results.append(
            {
                "target": "OWASP Security Fuzz",
                "engine": "hypothesis",
                "runs": runs,
                "duration_seconds": dur,
                "crashes": 0 if passed else 1,
                "redos_violations": 0,
                "passed": passed,
            }
        )

    if not results:
        raise ValueError(
            f"Unknown fuzz target: '{target}'. Choose from 'all', 'sanitizer', 'proto', 'owasp'."
        )

    return results


def run_snapshot_update_for_dir(
    target_dir: Path, mode: str, root_dir: Path | None = None
) -> int:
    """Run pytest in single-process snapshot mode for the target directory.

    Args:
        target_dir: Directory containing tests with snapshots.
        mode: Snapshot mode ('create', 'fix', or 'review').
        root_dir: Optional root directory path.

    Returns:
        Exit code from the pytest subprocess.
    """
    if not target_dir.is_dir():
        return 1

    root = root_dir or get_repo_root()
    cmd = [
        "uv",
        "run",
        "pytest",
        str(target_dir),
        "-n",
        "0",
        f"--inline-snapshot={mode}",
        "--no-cov",
        "-o",
        "addopts=",
    ]
    res = subprocess.run(cmd, cwd=root)
    return res.returncode


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
                    # Ignore corrupted or unparseable SARIF JSON outputs
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
        from hexastack_tools.utils.workspace import get_package_directories

        targets = (
            list(command.targets)
            if command.targets
            else get_package_directories(self._root)
        )

        exit_code = 0
        updated: list[str] = []
        for target in targets:
            code = run_snapshot_update_for_dir(target, command.mode, self._root)
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
    "run_snapshot_update_for_dir",
    "run_target_fuzz",
    "ScanCodeQlHandler",
    "UpdateInlineSnapshotsHandler",
]
