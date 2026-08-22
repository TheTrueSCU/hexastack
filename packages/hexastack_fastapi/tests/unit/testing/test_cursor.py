"""Unit tests for cursor test helpers."""

from hexastack_fastapi.testing.cursor import VIRTUAL_CURSOR_SCRIPT, smart_click


def test_cursor_helpers() -> None:
    assert callable(smart_click)
    assert "playwright-virtual-cursor" in VIRTUAL_CURSOR_SCRIPT
