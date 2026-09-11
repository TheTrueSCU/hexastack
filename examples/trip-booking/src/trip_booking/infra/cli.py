"""Typer CLI driving adapter for executing Trip Booking Sagas.

Notes/Architectural Intent:
    Provides an interactive terminal interface to execute and visualize distributed sagas,
    including simulating failure at any step to observe real-time LIFO compensation rollback.
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from trip_booking.domain.models import BookingStatus, TripBookingRequest
from trip_booking.infra.bootstrap import create_container

cli_app = typer.Typer(
    name="trip-booking",
    help="Distributed Saga Orchestration Reference CLI - Book trips and observe compensations.",
    no_args_is_help=True,
)
console = Console()


@cli_app.command("book")
def book_command(
    customer_id: str = typer.Option("cust-42", "--customer", "-c", help="Customer ID"),
    destination: str = typer.Option("Tokyo", "--destination", "-d", help="Destination city"),
    hotel_nights: int = typer.Option(4, "--nights", "-n", help="Number of hotel nights"),
    fail_at: str = typer.Option(
        "none",
        "--fail-at",
        "-f",
        help="Simulate failure at step: none, flight, hotel, car, payment",
    ),
) -> None:
    """Execute the Holiday Trip Booking Saga."""
    console.print(
        Panel.fit(
            f"[bold cyan]Executing Trip Booking Saga[/bold cyan]\n"
            f"Customer: [yellow]{customer_id}[/yellow] | Destination: [yellow]{destination}[/yellow]\n"
            f"Failure Injection: [bold red]{fail_at.upper()}[/bold red]",
            title="Hexastack Saga Orchestrator",
        )
    )

    container = create_container(
        fail_flight=(fail_at.lower() == "flight"),
        fail_hotel=(fail_at.lower() == "hotel"),
        fail_car=(fail_at.lower() == "car"),
        fail_payment=(fail_at.lower() == "payment"),
    )

    request = TripBookingRequest(
        customer_id=customer_id,
        customer_email=f"{customer_id}@example.com",
        destination=destination,
        departure_date="2026-10-01",
        return_date="2026-10-05",
        hotel_nights=hotel_nights,
        car_rental_days=hotel_nights,
    )

    summary = container.coordinator.execute(request)

    table = Table(title="Saga Execution Report")
    table.add_column("Property", style="bold")
    table.add_column("Value")

    table.add_row("Trip ID", summary.trip_id)
    table.add_row("Customer", summary.customer_id)
    table.add_row("Destination", summary.destination)

    status_color = "green" if summary.status == BookingStatus.CONFIRMED else "red"
    table.add_row("Final Status", f"[{status_color}]{summary.status.value}[/{status_color}]")
    table.add_row("Total Charged", f"${summary.total_cost:.2f}")

    if summary.status == BookingStatus.CONFIRMED:
        if summary.flight:
            table.add_row("Flight", f"{summary.flight.flight_number} (${summary.flight.price:.2f})")
        if summary.hotel:
            table.add_row("Hotel", f"{summary.hotel.hotel_name} (${summary.hotel.price:.2f})")
        if summary.car:
            table.add_row("Car Rental", f"{summary.car.vehicle_class} (${summary.car.price:.2f})")
        if summary.payment:
            table.add_row("Payment Ref", summary.payment.transaction_id)
    else:
        table.add_row("Triggering Fault", f"[red]{summary.error_message}[/red]")
        table.add_row(
            "Compensated Steps (LIFO)",
            f"[yellow]{' -> '.join(summary.compensated_steps) or 'None'}[/yellow]",
        )

    console.print(table)


@cli_app.command("version")
def version_command() -> None:
    """Show trip-booking reference service version."""
    console.print("trip-booking version 0.1.0")


def main() -> None:
    """CLI execution entrypoint."""
    cli_app()


__all__ = [
    "cli_app",
    "main",
]
