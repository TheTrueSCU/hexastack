"""Textual terminal UI presentation adapters for Hexastack.

Notes/Architectural Intent:
    Exports Textual operational dashboard components and lifecycle factories.
"""

from __future__ import annotations

from hexastack_ui.adapters.textual.dashboard import (
    TextualDevToolsApp,
    TextualDevToolsPresenter,
    check_textual_installed,
    mount_textual_dashboard,
)

__all__ = [
    "check_textual_installed",
    "mount_textual_dashboard",
    "TextualDevToolsApp",
    "TextualDevToolsPresenter",
]
