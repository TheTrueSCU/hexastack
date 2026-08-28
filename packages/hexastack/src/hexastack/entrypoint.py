import sys

from hexastack_core.infra.bootstrap import bootstrap


def main() -> None:
    """CLI script entrypoint executing the Hexastack diagnostic and inspection application."""
    import hexastack.adapters.cli as cli_module
    import hexastack.application.diagnostics as diag_module

    result = bootstrap(
        packages_to_scan=[
            diag_module,
            cli_module,
        ],
    )
    cli_app = result.get("cli_app")
    if cli_app is not None:
        cli_module.add_scaffold_commands(cli_app)
        cli_module.add_serve_command(cli_app)
        cli_module.add_dev_command(cli_app)
        cli_module.add_ui_commands(cli_app)
        cli_module.add_db_commands(cli_app)
        cli_module.add_mcp_commands(cli_app)
        cli_module.add_grpc_commands(cli_app)
        cli_module.add_profile_command(cli_app)
        cli_module.add_load_command(cli_app)
        cli_app()

    else:
        sys.stderr.write(
            "Error: hexastack-cli is required to run the CLI entrypoint.\n"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
