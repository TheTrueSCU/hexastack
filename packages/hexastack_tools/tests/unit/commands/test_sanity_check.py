"""Unit tests for the scoped sanity check command driving adapter.

Notes/Architectural Intent:
    Validates target resolution, CLI argument parsing, CommandBus dispatching,
    and GovernancePresenter integration within the driving adapter layer.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_cqrs.ports.buses import CommandBusPort
from hexastack_tools.commands.sanity_check import (
    CheckResult,
    SanityTarget,
    _build_parser,
    _create_example_target,
    _create_package_target,
    _detect_git_targets,
    main,
    resolve_targets,
    run_sanity_check,
)
from hexastack_tools.domain.governance import (
    CheckStatus,
    RunSanityCheckCommand,
    SanityCheckReport,
)
from hexastack_tools.ports.governance import GovernancePresenterPort


def test_create_targets(tmp_path: Path) -> None:
    """Verify target factory helpers."""
    pkg_dir = tmp_path / "pkg"
    (pkg_dir / "src").mkdir(parents=True)
    (pkg_dir / "tests").mkdir(parents=True)
    pkg_target = _create_package_target("pkg", pkg_dir)
    assert pkg_target.name == "pkg"
    assert pkg_target.kind == "package"
    assert len(pkg_target.src_paths) == 1

    ex_dir = tmp_path / "ex"
    ex_target = _create_example_target("ex", ex_dir)
    assert ex_target.name == "ex"
    assert ex_target.kind == "example"


def test_resolve_targets_package(tmp_path: Path) -> None:
    """Verify CLI argument resolution for explicit packages."""
    args = argparse.Namespace(
        packages=["cqrs"],
        examples=None,
        files=None,
        all_targets=False,
    )
    targets = resolve_targets(args, tmp_path)
    assert len(targets) == 1
    assert targets[0].name == "cqrs"
    assert targets[0].kind == "package"


def test_resolve_targets_example(tmp_path: Path) -> None:
    """Verify CLI argument resolution for explicit examples."""
    args = argparse.Namespace(
        packages=None,
        examples=["trip-booking"],
        files=None,
        all_targets=False,
    )
    targets = resolve_targets(args, tmp_path)
    assert len(targets) == 1
    assert targets[0].name == "trip-booking"
    assert targets[0].kind == "example"


def test_resolve_targets_explicit_file(tmp_path: Path) -> None:
    """Verify CLI argument resolution for explicit file paths."""
    sample_file = tmp_path / "mod.py"
    sample_file.write_text("x = 1\n", encoding="utf-8")

    args = argparse.Namespace(
        packages=None,
        examples=None,
        files=[str(sample_file)],
        all_targets=False,
    )
    targets = resolve_targets(args, tmp_path)
    assert len(targets) == 1
    assert targets[0].name == "mod.py"
    assert targets[0].kind == "file"


def test_detect_git_targets(tmp_path: Path) -> None:
    """Verify _detect_git_targets parses porcelain git status output."""
    git_stdout = (
        " M packages/hexastack_cqrs/src/mod.py\n?? examples/trip-booking/src/app.py\n"
    )
    mock_proc = MagicMock(stdout=git_stdout)

    with (
        patch("subprocess.run", return_value=mock_proc),
        patch(
            "hexastack_tools.commands.sanity_check.get_package_directory",
            return_value=tmp_path,
        ),
        patch(
            "hexastack_tools.commands.sanity_check.get_example_directory",
            return_value=tmp_path,
        ),
        patch("pathlib.Path.is_dir", return_value=True),
    ):
        targets = _detect_git_targets(tmp_path)
        names = {t.name for t in targets}
        assert "hexastack_cqrs" in names
        assert "trip-booking" in names


def test_run_sanity_check_with_bus_and_presenter(tmp_path: Path) -> None:
    """Verify run_sanity_check dispatches RunSanityCheckCommand and delegates to presenter."""
    mock_bus = MagicMock(spec=CommandBusPort)
    mock_presenter = MagicMock(spec=GovernancePresenterPort)

    dummy_report = SanityCheckReport(
        results=(CheckResult("Ruff", "pkg", CheckStatus.PASS, 0.05),),
        total_duration=0.05,
        exit_code=0,
    )
    mock_bus.dispatch.return_value = dummy_report
    mock_presenter.present_sanity_dashboard.return_value = 0

    target = SanityTarget("pkg", "package", tmp_path, (), ())
    exit_code = run_sanity_check(
        targets=[target],
        repo_root=tmp_path,
        bus=mock_bus,
        presenter=mock_presenter,
    )

    assert exit_code == 0
    mock_bus.dispatch.assert_called_once()
    cmd = mock_bus.dispatch.call_args[0][0]
    assert isinstance(cmd, RunSanityCheckCommand)
    assert len(cmd.targets) == 1
    mock_presenter.present_sanity_dashboard.assert_called_once_with(dummy_report)


def test_parser_and_main(tmp_path: Path) -> None:
    """Verify argument parser and main entrypoint flow."""
    parser = _build_parser()
    parsed = parser.parse_args(["-p", "cqrs", "--fix", "--skip-tests", "-mx", "20"])
    assert parsed.packages == ["cqrs"]
    assert parsed.fix is True
    assert parsed.skip_tests is True
    assert parsed.max_complexity == 20

    with (
        patch(
            "sys.argv",
            ["sanity-check", "-p", "cqrs", "--skip-tests"],
        ),
        patch(
            "hexastack_tools.commands.sanity_check.get_repo_root",
            return_value=tmp_path,
        ),
        patch(
            "hexastack_tools.commands.sanity_check.resolve_targets",
            return_value=[SanityTarget("cqrs", "package", tmp_path, (), ())],
        ),
        patch(
            "hexastack_tools.commands.sanity_check.run_sanity_check",
            return_value=0,
        ) as mock_run,
        patch("sys.exit") as mock_exit,
    ):
        main()
        mock_run.assert_called_once()
        mock_exit.assert_called_once_with(0)
