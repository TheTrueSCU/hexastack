"""Unit tests for check-extras-parity tool command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from hexastack_tools.commands.extras_parity import (
    ExtraParityViolation,
    audit_extras_parity,
    generate_extras_mermaid_diagram,
    main,
)
from hexastack_tools.domain.dependencies import (
    AuditExtrasParityCommand,
    ExtrasAuditResult,
)
from hexastack_tools.ports.dependencies import DependencyPresenterPort
from hexastack_tools.utils.workspace import get_repo_root


def test_extras_parity_callables_exist() -> None:
    """Verify extras parity validator exports are defined and callable."""
    assert callable(audit_extras_parity)
    assert callable(generate_extras_mermaid_diagram)
    assert callable(main)
    assert ExtraParityViolation is not None


def test_audit_extras_parity_passes_on_current_workspace() -> None:
    """Verify that current repository workspace has 100% extras parity."""
    repo_root = get_repo_root()
    violations = audit_extras_parity(repo_root)
    assert violations == []


def test_audit_extras_parity_flags_missing_umbrella_file(tmp_path: Path) -> None:
    """Verify validator flags missing umbrella pyproject.toml."""
    violations = audit_extras_parity(tmp_path)
    assert len(violations) == 1
    assert violations[0].extra_name == "<root>"


def test_main_dispatches_and_presents() -> None:
    """Verify main dispatches AuditExtrasParityCommand and delegates to presenter."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = ExtrasAuditResult(
        violations=(),
        total_packages_checked=5,
    )
    mock_presenter = MagicMock(spec=DependencyPresenterPort)
    mock_presenter.present_extras_parity.return_value = 0

    with (
        patch(
            "hexastack_tools.commands.extras_parity.create_governance_bus",
            return_value=mock_bus,
        ),
        patch(
            "hexastack_tools.commands.extras_parity.create_dependency_presenter",
            return_value=mock_presenter,
        ) as mock_create_presenter,
    ):
        exit_code = main(["-f", "json"])
        assert exit_code == 0
        mock_create_presenter.assert_called_once_with("json")
        mock_bus.dispatch.assert_called_once()
        cmd = mock_bus.dispatch.call_args[0][0]
        assert isinstance(cmd, AuditExtrasParityCommand)
        assert cmd.generate_diagram is False
        mock_presenter.present_extras_parity.assert_called_once_with(
            mock_bus.dispatch.return_value
        )


def test_main_diagram_flag() -> None:
    """Verify main passes diagram string to presenter when --diagram is given."""
    mock_bus = MagicMock()
    mock_bus.dispatch.return_value = "```mermaid\ngraph LR\n```"
    mock_presenter = MagicMock(spec=DependencyPresenterPort)
    mock_presenter.present_extras_parity.return_value = 0

    with (
        patch(
            "hexastack_tools.commands.extras_parity.create_governance_bus",
            return_value=mock_bus,
        ),
        patch(
            "hexastack_tools.commands.extras_parity.create_dependency_presenter",
            return_value=mock_presenter,
        ),
    ):
        exit_code = main(["--diagram"])
        assert exit_code == 0
        mock_presenter.present_extras_parity.assert_called_once()
        _, kwargs = mock_presenter.present_extras_parity.call_args
        assert kwargs.get("diagram") == "```mermaid\ngraph LR\n```"
