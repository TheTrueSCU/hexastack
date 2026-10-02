"""Testing utilities and fixtures for Hexastack FastAPI and DevTools applications."""

from hexastack_fastapi.testing.cursor import VIRTUAL_CURSOR_SCRIPT, smart_click
from hexastack_fastapi.testing.recorder import DemoNarrator
from hexastack_fastapi.testing.server import (
    EphemeralServer,
    ephemeral_server,
    find_free_port,
)

__all__ = [
    "DemoNarrator",
    "ephemeral_server",
    "EphemeralServer",
    "find_free_port",
    "smart_click",
    "VIRTUAL_CURSOR_SCRIPT",
]
