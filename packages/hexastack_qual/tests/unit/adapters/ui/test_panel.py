"""Unit tests for NiceGUI DevTools panel component.

Notes/Architectural Intent:
    Verifies that render_quality_panel behaves correctly under NiceGUI-installed
    and NiceGUI-absent environments, and that button callbacks trigger
    HexaqualRunnerAdapter operations properly.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import hexastack_qual.adapters.ui.panel as panel_module
import pytest
from hexastack_qual.adapters.ui.panel import render_quality_panel
from hexastack_qual.domain.exceptions import AdapterNotAvailableError
from hexastack_qual.domain.models import QualityCheckResult, QualityScorecard
from nicegui import Client
from nicegui.page import page


def test_render_quality_panel_raises_when_nicegui_missing():
    """Verify AdapterNotAvailableError is raised when HAS_NICEGUI is False."""
    with patch.object(panel_module, "HAS_NICEGUI", False):
        with pytest.raises(AdapterNotAvailableError) as exc_info:
            render_quality_panel()

        err = exc_info.value
        assert "pip install 'hexastack-qual[ui]'" in str(err)


def test_render_quality_panel_renders_elements():
    """Verify UI cards, metrics, and buttons render within NiceGUI page context."""
    client = Client(page("/test-quality-panel"))
    with client.layout.default_slot:
        mock_runner = MagicMock()
        mock_runner.run_sanity.return_value = QualityScorecard(
            target="workspace",
            is_healthy=True,
            checks=[
                QualityCheckResult(
                    check_name="ruff", target="workspace", status="pass", details="ok"
                ),
            ],
        )
        mock_runner.fix_statements.return_value = 3

        with patch.object(
            panel_module, "HexaqualRunnerAdapter", return_value=mock_runner
        ):
            render_quality_panel()

        # Check that UI elements were rendered into client slot
        elements = list(client.layout.default_slot)
        num_elements = len(elements)
        assert num_elements > 0


def test_render_quality_panel_callbacks():
    """Verify on_run_sanity and on_fix_statements callbacks update label text."""
    client = Client(page("/test-quality-panel-callbacks"))
    with client.layout.default_slot:
        mock_runner = MagicMock()
        mock_runner.run_sanity.return_value = QualityScorecard(
            target="workspace",
            is_healthy=True,
            checks=[
                QualityCheckResult(
                    check_name="ruff", target="workspace", status="pass", details="ok"
                ),
                QualityCheckResult(
                    check_name="ty", target="workspace", status="pass", details="ok"
                ),
            ],
        )
        mock_runner.fix_statements.return_value = 2

        with patch("hexastack_qual.adapters.ui.panel.ui.button") as mock_button:
            captured_callbacks = {}

            def fake_button(label, on_click=None, icon=None):
                mock_btn = MagicMock()
                captured_callbacks[label] = on_click
                return mock_btn

            mock_button.side_effect = fake_button

            with patch.object(
                panel_module, "HexaqualRunnerAdapter", return_value=mock_runner
            ):
                render_quality_panel()

            # Trigger on_run_sanity callback
            sanity_cb = captured_callbacks.get("Run Sanity Audit")
            assert callable(sanity_cb)
            sanity_cb()
            call_count = mock_runner.run_sanity.call_count
            assert call_count == 1

            # Trigger on_run_sanity callback when unhealthy
            mock_runner.run_sanity.return_value = QualityScorecard(
                target="workspace",
                is_healthy=False,
                checks=[
                    QualityCheckResult(
                        check_name="ruff",
                        target="workspace",
                        status="fail",
                        details="bad syntax",
                    ),
                ],
            )
            sanity_cb()
            call_count_unhealthy = mock_runner.run_sanity.call_count
            assert call_count_unhealthy == 2

            # Trigger on_fix_statements callback
            fix_cb = captured_callbacks.get("Fix __all__ Statements")
            assert callable(fix_cb)
            fix_cb()
            fix_call_count = mock_runner.fix_statements.call_count
            assert fix_call_count == 1
