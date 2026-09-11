"""Bootstrap container and dependency injection wiring for the Trip Booking service.

Notes/Architectural Intent:
    Assembles domain services, saga coordinator, and driving adapters.
    Enables zero-dependency local execution and clean testing injection.
"""

from __future__ import annotations

from dataclasses import dataclass

from trip_booking.adapters.driven.in_memory import (
    InMemoryCarRentalService,
    InMemoryFlightService,
    InMemoryHotelService,
    InMemoryPaymentService,
)
from trip_booking.infra.saga import TripBookingCoordinator


@dataclass
class TripBookingServiceContainer:
    """Container holding instantiated adapters and coordinators."""

    flight_service: InMemoryFlightService
    hotel_service: InMemoryHotelService
    car_service: InMemoryCarRentalService
    payment_service: InMemoryPaymentService
    coordinator: TripBookingCoordinator


def create_container(
    fail_flight: bool = False,
    fail_hotel: bool = False,
    fail_car: bool = False,
    fail_payment: bool = False,
) -> TripBookingServiceContainer:
    """Factory creating and wiring an in-memory TripBooking service instance.

    Args:
        fail_flight: Injects failure into flight booking step.
        fail_hotel: Injects failure into hotel reservation step.
        fail_car: Injects failure into car rental step.
        fail_payment: Injects failure into payment charge step.

    Returns:
        TripBookingServiceContainer with configured services and coordinator.
    """
    flight_svc = InMemoryFlightService(should_fail=fail_flight)
    hotel_svc = InMemoryHotelService(should_fail=fail_hotel)
    car_svc = InMemoryCarRentalService(should_fail=fail_car)
    payment_svc = InMemoryPaymentService(should_fail=fail_payment)

    coordinator = TripBookingCoordinator(
        flight_service=flight_svc,
        hotel_service=hotel_svc,
        car_rental_service=car_svc,
        payment_service=payment_svc,
    )

    return TripBookingServiceContainer(
        flight_service=flight_svc,
        hotel_service=hotel_svc,
        car_service=car_svc,
        payment_service=payment_svc,
        coordinator=coordinator,
    )


__all__ = [
    "TripBookingServiceContainer",
    "create_container",
]
