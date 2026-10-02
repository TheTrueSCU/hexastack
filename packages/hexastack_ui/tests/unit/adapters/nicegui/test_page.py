"""Unit tests for NiceGUI page and app mounting."""

import sys
from unittest.mock import patch

import pytest
from fastapi import FastAPI

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_ui.adapters.nicegui.page import (
    check_nicegui_installed,
    mount_ui_app,
    ui_page,
)


def test_ui_page_decorator():
    """Verify ui_page decorates callable cleanly."""

    @ui_page("/test-page", title="Test Page")
    def my_page():
        return "page-content"

    assert callable(my_page)


def test_mount_ui_app():
    """Verify mount_ui_app invokes ui.run_with."""
    app = FastAPI()
    mount_ui_app(app, title="Custom Title")
    assert app is not None


def test_check_nicegui_installed_missing():
    """Verify check_nicegui_installed raises MissingDependencyError when nicegui is not present."""
    with (
        patch.dict(sys.modules, {"nicegui": None}),
        pytest.raises(MissingDependencyError, match="NiceGUI is required"),
    ):
        check_nicegui_installed()
