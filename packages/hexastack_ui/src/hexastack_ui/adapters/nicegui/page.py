"""NiceGUI reactive page and mounting primitives.

Notes/Architectural Intent:
    Provides decorators and mounting functions for integrating NiceGUI with FastAPI/Starlette.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from hexastack_core.domain.exceptions import MissingDependencyError

__all__ = [
    "check_nicegui_installed",
    "mount_ui_app",
    "ui_page",
]


def check_nicegui_installed() -> None:
    """Verify NiceGUI is available in runtime environment.

    Raises:
        MissingDependencyError: If NiceGUI is not installed.

    Notes/Architectural Intent:
        Enables lazy import error reporting with installation hints.
    """
    try:
        import nicegui  # noqa: F401
    except ImportError as e:
        raise MissingDependencyError(
            "NiceGUI is required for hexastack-ui NiceGUI support. "
            "Install with 'pip install hexastack-ui[nicegui]' or 'pip install nicegui'."
        ) from e


def ui_page(
    path: str,
    *,
    title: str | None = None,
    viewport: str | None = None,
    favicon: str | None = None,
    dark: bool | None = None,
    response_timeout: float = 3.0,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Declarative decorator registering a NiceGUI reactive UI page.

    Args:
        path: URL path for the page (e.g. '/dashboard', '/users').
        title: Optional browser tab title.
        viewport: Optional viewport meta tag string.
        favicon: Optional favicon path or URL.
        dark: Optional dark mode setting (True/False/None).
        response_timeout: Maximum seconds to wait for client connection response.

    Returns:
        Decorated page function.

    Raises:
        MissingDependencyError: If NiceGUI is not installed.

    Notes/Architectural Intent:
        Wraps `nicegui.ui.page` while cleanly decoupling application modules from
        direct NiceGUI hard dependency at module import time.
    """
    check_nicegui_installed()
    from nicegui import ui

    return ui.page(
        path,
        title=title,
        viewport=viewport,
        favicon=favicon,
        dark=dark,
        response_timeout=response_timeout,
    )


def mount_ui_app(
    app: Any,
    *,
    title: str = "Hexastack UI",
    viewport: str = "width=device-width, initial-scale=1",
    favicon: str | None = None,
    dark: bool | None = None,
) -> None:
    """Mount NiceGUI reactive engine onto an existing FastAPI/Starlette application instance.

    Args:
        app: Target FastAPI or Starlette application.
        title: Application default page title.
        viewport: Viewport meta tag.
        favicon: Optional favicon.
        dark: Dark mode preference.

    Returns:
        None.

    Raises:
        MissingDependencyError: If NiceGUI is not installed.

    Notes/Architectural Intent:
        Integrates NiceGUI's Socket.IO and static assets into the host server lifecycle.
    """
    check_nicegui_installed()
    from nicegui import ui

    ui.run_with(
        app,
        title=title,
        viewport=viewport,
        favicon=favicon,
        dark=dark,
    )
