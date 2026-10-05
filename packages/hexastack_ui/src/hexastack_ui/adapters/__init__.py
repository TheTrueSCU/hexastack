"""UI presentation adapters for Hexastack."""

from hexastack_ui.adapters.nicegui import (
    check_nicegui_installed,
    dispatch_command,
    dispatch_query,
    mount_devtools_dashboard,
    mount_ui_app,
    ui_page,
)
from hexastack_ui.adapters.textual import (
    TextualDevToolsApp,
    TextualDevToolsPresenter,
    check_textual_installed,
    mount_textual_dashboard,
)

__all__ = [
    "check_nicegui_installed",
    "check_textual_installed",
    "dispatch_command",
    "dispatch_query",
    "mount_devtools_dashboard",
    "mount_textual_dashboard",
    "mount_ui_app",
    "TextualDevToolsApp",
    "TextualDevToolsPresenter",
    "ui_page",
]
