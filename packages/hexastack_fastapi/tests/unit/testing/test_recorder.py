"""Unit tests for response recorder helpers."""

from hexastack_fastapi.testing.recorder import DemoNarrator


def test_demo_narrator_attributes() -> None:
    assert hasattr(DemoNarrator, "step")
    assert hasattr(DemoNarrator, "goto")
    assert hasattr(DemoNarrator, "click")
    assert hasattr(DemoNarrator, "fill")
    assert hasattr(DemoNarrator, "finish")
