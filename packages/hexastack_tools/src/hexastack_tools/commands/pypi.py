"""PyPI package distribution commands."""

from __future__ import annotations

import sys

from scripts.pypi.build import main as _build_main
from scripts.pypi.check import main as _check_main
from scripts.pypi.publish import main as _publish_main


def build_main() -> None:
    """CLI entrypoint for pypi-build."""
    sys.exit(_build_main())


def check_main() -> None:
    """CLI entrypoint for pypi-check."""
    sys.exit(_check_main())


def publish_main() -> None:
    """CLI entrypoint for pypi-publish."""
    sys.exit(_publish_main())


__all__ = [
    "build_main",
    "check_main",
    "publish_main",
]
