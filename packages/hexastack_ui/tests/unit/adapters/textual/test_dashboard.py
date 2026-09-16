"""Unit tests for Textual DevTools dashboard adapter."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_ui.adapters.textual import (
    TextualDevToolsApp,
    TextualDevToolsPresenter,
    check_textual_installed,
    mount_textual_dashboard,
)
from hexastack_ui.domain.models import (
    CQRSMessageSummary,
    DevToolsDashboardState,
    FeatureFlagSummary,
    ServiceBindingSummary,
)


def test_check_textual_installed_success() -> None:
    """Verify check_textual_installed passes when textual is present."""
    result = check_textual_installed()
    assert result is None


def test_check_textual_installed_missing() -> None:
    """Verify check_textual_installed raises MissingDependencyError when textual is missing."""
    with patch.dict(sys.modules, {"textual": None}):
        with pytest.raises(MissingDependencyError) as exc_info:
            check_textual_installed()
        err_msg = str(exc_info.value)
        assert "Textual is required" in err_msg


@pytest.mark.asyncio
async def test_textual_app_default_state() -> None:
    """Verify TextualDevToolsApp runs with default state and initializes empty tables."""
    app = mount_textual_dashboard()
    is_app = app is not None
    assert is_app

    async with app.run_test() as pilot:
        cqrs_table = app.query_one("#cqrs-table")
        cqrs_count = cqrs_table.row_count
        assert cqrs_count == 0

        flags_table = app.query_one("#flags-table")
        flags_count = flags_table.row_count
        assert flags_count == 0

        services_table = app.query_one("#services-table")
        services_count = services_table.row_count
        assert services_count == 0

        mw_table = app.query_one("#middlewares-table")
        mw_count = mw_table.row_count
        assert mw_count == 0

        await pilot.press("d")
        dark_mode = app.theme
        assert dark_mode is not None


@pytest.mark.asyncio
async def test_textual_app_with_populated_state() -> None:
    """Verify TextualDevToolsApp populates rows according to provided DevToolsDashboardState."""
    state = DevToolsDashboardState(
        commands=[
            CQRSMessageSummary(
                name="CreateOrder", message_type="Command", module="domain.commands"
            )
        ],
        queries=[
            CQRSMessageSummary(
                name="GetOrder", message_type="Query", module="domain.queries"
            )
        ],
        flags=[
            FeatureFlagSummary(
                key="beta_pricing", enabled=True, description="Enable dynamic pricing"
            ),
            FeatureFlagSummary(
                key="audit_v2", enabled=False, description="Legacy audit logger"
            ),
        ],
        services=[
            ServiceBindingSummary(
                service="OrderRepositoryPort",
                module="domain.ports",
                resolver="PostgresOrderRepository",
            )
        ],
        middlewares=["CorrelationMiddleware", "MetricsMiddleware"],
    )

    app = TextualDevToolsApp(state=state)
    async with app.run_test() as _pilot:
        cqrs_table = app.query_one("#cqrs-table")
        cqrs_count = cqrs_table.row_count
        assert cqrs_count == 2

        flags_table = app.query_one("#flags-table")
        flags_count = flags_table.row_count
        assert flags_count == 2

        services_table = app.query_one("#services-table")
        services_count = services_table.row_count
        assert services_count == 1

        mw_table = app.query_one("#middlewares-table")
        mw_count = mw_table.row_count
        assert mw_count == 2


def test_textual_presenter_render_dashboard() -> None:
    """Verify TextualDevToolsPresenter instantiates and runs the Textual app."""
    presenter = TextualDevToolsPresenter()
    mock_app = MagicMock()

    with patch(
        "hexastack_ui.adapters.textual.dashboard.TextualDevToolsApp",
        return_value=mock_app,
    ) as mock_factory:
        dummy_state = DevToolsDashboardState()
        presenter.render_dashboard(dummy_state)
        mock_factory.assert_called_once_with(state=dummy_state)
        mock_app.run.assert_called_once()
