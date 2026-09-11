"""Port interfaces defining external system contracts."""

from trip_booking.ports.services import (
    CarRentalPort,
    FlightServicePort,
    HotelServicePort,
    PaymentServicePort,
)

__all__ = [
    "CarRentalPort",
    "FlightServicePort",
    "HotelServicePort",
    "PaymentServicePort",
]
