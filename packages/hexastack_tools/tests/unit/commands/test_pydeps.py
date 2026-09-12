"""Unit tests for pydeps command."""

from unittest.mock import MagicMock, patch

from hexastack_tools.commands.pydeps import generate_main
from hexastack_tools.domain.generators import PydepsDiagramResult, PydepsReport


def test_pydeps_generate_main_callable() -> None:
    """Verify pydeps generate main callable."""
    assert callable(generate_main)


def test_pydeps_generate_main_dispatches_bus() -> None:
    """Verify generate_main parses args, dispatches GeneratePydepsCommand, and formats."""
    mock_bus = MagicMock()
    mock_report = PydepsReport(
        results=(
            PydepsDiagramResult(
                name="core", path="docs/assets/pydeps/core.svg", success=True
            ),
        ),
        is_successful=True,
    )
    mock_bus.dispatch.return_value = mock_report

    with (
        patch("hexastack_tools.commands.pydeps.ensure_tool_installed"),
        patch(
            "hexastack_tools.infra.bootstrap.create_governance_bus",
            return_value=mock_bus,
        ),
    ):
        code = generate_main(["-p", "core", "--format", "json"])
        assert code == 0
        assert mock_bus.dispatch.called
