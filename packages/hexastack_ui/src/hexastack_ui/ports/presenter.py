"""Abstract presentation ports for Hexastack UI integrations.

Notes/Architectural Intent:
    Defines UI framework-agnostic interfaces for rendering developer consoles,
    mounting web/TUI application lifecycles, and collecting diagnostic state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from hexastack_ui.domain.models import DevToolsDashboardState

__all__ = [
    "DevToolsPresenterPort",
    "UIPresenterPort",
]


class UIPresenterPort(ABC):
    """Abstract port for mounting and lifecycle management of UI presentation engines."""

    @abstractmethod
    def mount(self, target_app: Any, **kwargs: Any) -> None:
        """Mount UI presentation engine onto a host server or execution runtime.

        Args:
            target_app: Target application or server instance.
            **kwargs: Additional framework-specific configuration options.

        Returns:
            None.

        Raises:
            Exception: If mounting fails.

        Notes/Architectural Intent:
            Enables generic mounting logic across HTTP servers (FastAPI/Starlette) or TUI runtimes.
        """


class DevToolsPresenterPort(ABC):
    """Abstract port for rendering interactive DevTools diagnostic dashboards."""

    @abstractmethod
    def render_dashboard(
        self, state: DevToolsDashboardState, target_app: Any, **kwargs: Any
    ) -> None:
        """Render diagnostic dashboard given a snapshot of the runtime state.

        Args:
            state: Current aggregated runtime state.
            target_app: Host application instance.
            **kwargs: Additional presentation parameters.

        Returns:
            None.

        Raises:
            Exception: If dashboard rendering fails.

        Notes/Architectural Intent:
            Decouples dashboard visualization (NiceGUI, Textual) from state extraction.
        """
