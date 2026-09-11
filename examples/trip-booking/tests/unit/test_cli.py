"""Unit tests for Typer CLI driving adapter."""

from typer.testing import CliRunner

from trip_booking.infra.cli import cli_app

runner = CliRunner()


def test_cli_book_success() -> None:
    """Verify CLI book command without failures."""
    result = runner.invoke(
        cli_app, ["book", "--customer", "cust-cli", "--destination", "Kyoto"]
    )
    code = result.exit_code
    assert code == 0
    output = result.stdout
    assert "CONFIRMED" in output
    assert "Kyoto" in output


def test_cli_book_failure_injection() -> None:
    """Verify CLI book command with simulated failure."""
    result = runner.invoke(
        cli_app,
        ["book", "--customer", "cust-cli", "--destination", "Rome", "--fail-at", "car"],
    )
    code = result.exit_code
    assert code == 0
    output = result.stdout
    assert "CANCELLED" in output
    assert "ReserveHotel -> BookFlight" in output
