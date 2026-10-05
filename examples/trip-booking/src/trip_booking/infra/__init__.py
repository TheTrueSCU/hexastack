"""Infrastructure layer providing saga assembly, bootstrap, and CLI execution."""

from trip_booking.infra.bootstrap import (
    TripBookingServiceContainer,
    create_container,
)
from trip_booking.infra.cli import cli_app, main
from trip_booking.infra.saga import TripBookingCoordinator

__all__ = [
    "TripBookingCoordinator",
    "TripBookingServiceContainer",
    "cli_app",
    "create_container",
    "main",
]
