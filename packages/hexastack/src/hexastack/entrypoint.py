import sys

from hexastack_core.infra.bootstrap import bootstrap


def main() -> None:
    """CLI script entrypoint executing the Hexastack diagnostic and inspection application."""
    import hexastack.adapters.cli
    import hexastack.application.diagnostics
<<<<<<< Updated upstream
    from hexastack.adapters.cli import add_serve_command
=======
    from hexastack.adapters.cli import add_db_commands, add_serve_command
>>>>>>> Stashed changes

    result = bootstrap(
        packages_to_scan=[
            hexastack.application.diagnostics,
            hexastack.adapters.cli,
        ],
    )
    cli_app = result.get("cli_app")
    if cli_app is not None:
        add_serve_command(cli_app)
<<<<<<< Updated upstream
        cli_app()
    else:
        sys.stderr.write("Error: hexastack-cli is required to run the CLI entrypoint.\n")
=======
        add_db_commands(cli_app)
        cli_app()
    else:
        sys.stderr.write(
            "Error: hexastack-cli is required to run the CLI entrypoint.\n"
        )
>>>>>>> Stashed changes
        sys.exit(1)


if __name__ == "__main__":
    main()
