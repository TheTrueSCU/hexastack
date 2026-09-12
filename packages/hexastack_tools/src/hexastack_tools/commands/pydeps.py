"""Programmatically generate architecture dependency diagrams using pydeps."""

from __future__ import annotations

from hexastack_tools.utils.pydeps import (
    generate_all_diagrams,
    generate_overview_diagram,
    generate_package_diagram,
)
from hexastack_tools.utils.workspace import (
    HexastackScriptArgumentParser,
    ensure_tool_installed,
)

__all__ = [
    "generate_all_diagrams",
    "generate_main",
    "generate_overview_diagram",
    "generate_package_diagram",
]


def generate_main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for pydeps-generate.

    Args:
        argv: Optional command-line arguments list.

    Returns:
        Exit code (0 for success, non-zero for failure).

    Notes/Architectural Intent:
        Dispatches GeneratePydepsCommand across the governance bus and renders
        results via the configured GeneratorPresenterPort.
    """
    ensure_tool_installed("pydeps", cli_command="pydeps", extra_name="diagrams")

    parser = HexastackScriptArgumentParser(
        description="Generate architecture dependency diagrams using pydeps."
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["table", "json", "markdown"],
        default="table",
        help="Output presentation format (default: table).",
    )
    args = parser.parse_args(argv)

    from hexastack_tools.adapters.presenters.generators import (
        create_generator_presenter,
    )
    from hexastack_tools.domain.generators import GeneratePydepsCommand
    from hexastack_tools.infra.bootstrap import create_governance_bus

    bus = create_governance_bus()
    presenter = create_generator_presenter(args.format)

    cmd = GeneratePydepsCommand(
        packages=tuple(args.packages) if args.packages else (),
    )
    report = bus.dispatch(cmd)
    return presenter.present_pydeps(report)
