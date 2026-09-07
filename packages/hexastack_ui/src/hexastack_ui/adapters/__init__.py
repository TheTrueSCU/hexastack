"""UI presentation adapters for Hexastack."""

from hexastack_ui.adapters.nicegui import (
    check_nicegui_installed,
    dispatch_command,
    dispatch_query,
    mount_devtools_dashboard,
    mount_ui_app,
    ui_page,
)

__all__ = [
    "check_nicegui_installed",
    "dispatch_command",
    "dispatch_query",
    "mount_devtools_dashboard",
    "mount_ui_app",
    "ui_page",
]
