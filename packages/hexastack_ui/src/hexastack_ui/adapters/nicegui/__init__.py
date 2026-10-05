"""NiceGUI reactive presentation adapter and DevTools dashboard."""

from hexastack_ui.adapters.nicegui.devtools import mount_devtools_dashboard
from hexastack_ui.adapters.nicegui.dispatch import (
    dispatch_command,
    dispatch_query,
)
from hexastack_ui.adapters.nicegui.page import (
    check_nicegui_installed,
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
