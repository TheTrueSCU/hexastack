"""Typer CLI driving command adapter bindings."""

from __future__ import annotations

from hexastack_cli.infra.decorators import cli_command

from financial_ledger.domain.commands import (
    CreateAccountCommand,
    FreezeAccountCommand,
    TransferMoneyCommand,
)

__all__ = []

cli_command("create-account", help="Create a new ledger account.")(CreateAccountCommand)
cli_command("freeze-account", help="Freeze a ledger account.")(FreezeAccountCommand)
cli_command("transfer", help="Transfer funds between two accounts.")(TransferMoneyCommand)
