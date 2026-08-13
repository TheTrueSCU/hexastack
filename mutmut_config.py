"""Mutmut configuration file for Hexastack.

Notes/Architectural Intent:
    Filters out non-logical boilerplate, type annotations, logging strings,
    and registration metadata to eliminate false positives in mutation testing.
"""

from typing import Any


def pre_mutation(context: Any) -> None:
    """Filter out non-logical mutations before executing test runner.

    Args:
        context: Mutmut Context object containing filename, source_code, node, etc.

    Returns:
        None.
    """
    line = getattr(context, "current_source_line", "").strip()

    # 1. Skip explicit no-mutate and no-cover directives
    if "pragma: no mutate" in line or "pragma: no cover" in line:
        context.skip = True
        return

    # 2. Skip __all__ definitions and module export lists
    if "__all__" in line or line.startswith("__all__"):
        context.skip = True
        return

    # 3. Skip type annotations, TYPE_CHECKING blocks, and import statements
    if (
        line.startswith("if TYPE_CHECKING:")
        or line.startswith("from ")
        or line.startswith("import ")
    ):
        context.skip = True
        return

    # 4. Skip structured logging statements
    if any(
        line.startswith(f"logger.{level}") or f"logger.{level}(" in line
        for level in ("debug", "info", "warning", "trace", "log")
    ):
        context.skip = True
        return

    # 5. Skip decorator headers
    if (
        line.startswith("@")
        or "@config_section" in line
        or "@command_handler" in line
        or "@query_handler" in line
    ):
        context.skip = True
        return

    # 6. Skip docstring blocks and pure comments
    if line.startswith('"""') or line.startswith("'''") or line.startswith("#"):
        context.skip = True
        return

    # 7. Skip Pydantic Field metadata definitions
    if "Field(" in line and (
        "description=" in line or "default=" in line or "default_factory=" in line
    ):
        context.skip = True
        return
