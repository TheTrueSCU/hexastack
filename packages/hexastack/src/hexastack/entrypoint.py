import sys

from hexastack_core.infra.bootstrap import bootstrap


def main() -> None:
    """CLI script entrypoint executing the Hexastack diagnostic and inspection application."""
    import hexastack.adapters.cli
    import hexastack.application.diagnostics
    from hexastack.adapters.cli import (
        add_db_commands,
        add_grpc_commands,
        add_mcp_commands,
        add_serve_command,
        add_ui_commands,
    )

    result = bootstrap(
        packages_to_scan=[
            hexastack.application.diagnostics,
            hexastack.adapters.cli,
        ],
    )
    cli_app = result.get("cli_app")
    if cli_app is not None:
        add_serve_command(cli_app)
        add_ui_commands(cli_app)
        add_db_commands(cli_app)
        add_mcp_commands(cli_app)
        add_grpc_commands(cli_app)
        cli_app()
    else:
        sys.stderr.write(
            "Error: hexastack-cli is required to run the CLI entrypoint.\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
