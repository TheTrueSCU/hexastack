"""Unit tests for terminal testing helpers."""

from hexastack_cli.testing.terminal import render_cli_demo_video


def test_render_cli_demo_video_callable() -> None:
    assert callable(render_cli_demo_video)
