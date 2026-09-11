"""Domain models and value objects for the Trip Booking microservice.

Notes/Architectural Intent:
    Pure domain entities representing travel reservations and transactional state.
    Strictly isolated from persistence, HTTP schemas, and orchestrator implementations.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class BookingStatus(StrEnum):
    """Lifecycle status of an individual booking or complete trip itinerary.

    Notes/Architectural Intent:
        Explicit status states distinguishing forward confirmation from compensation unwinding.
    """

    CANCELLED = "CANCELLED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    PENDING = "PENDING"


class TripBookingRequest(BaseModel):
    """Input parameters requested by a customer for an end-to-end trip booking.

    Notes/Architectural Intent:
        Domain request object used to initialize and parameterize the booking saga.
    """

    model_config = ConfigDict(frozen=True)

    customer_id: str
    customer_email: str
    destination: str
    departure_date: str
    return_date: str
    hotel_nights: int = Field(default=3, ge=1)
    car_rental_days: int = Field(default=3, ge=1)
    car_class: str = "SUV"


class FlightReservation(BaseModel):
    """Domain model representing a confirmed or cancelled flight booking.

    Notes/Architectural Intent:
        Represents the state of a flight segment within the distributed transaction.
    """

    model_config = ConfigDict(frozen=True)

    reservation_id: str = Field(default_factory=lambda: f"flt-{uuid4().hex[:8]}")
    customer_id: str
    flight_number: str
    destination: str
    seat: str
    price: float
    status: BookingStatus = BookingStatus.CONFIRMED


class HotelReservation(BaseModel):
    """Domain model representing a confirmed or cancelled hotel stay.

    Notes/Architectural Intent:
        Represents accommodation reservation state.
    """

    model_config = ConfigDict(frozen=True)

    reservation_id: str = Field(default_factory=lambda: f"htl-{uuid4().hex[:8]}")
    customer_id: str
    hotel_name: str
    destination: str
    nights: int
    price: float
    status: BookingStatus = BookingStatus.CONFIRMED


class CarReservation(BaseModel):
    """Domain model representing a confirmed or cancelled car rental.

    Notes/Architectural Intent:
        Represents ground transportation reservation state.
    """

    model_config = ConfigDict(frozen=True)

    reservation_id: str = Field(default_factory=lambda: f"car-{uuid4().hex[:8]}")
    customer_id: str
    vehicle_class: str
    rental_days: int
    price: float
    status: BookingStatus = BookingStatus.CONFIRMED


class PaymentReceipt(BaseModel):
    """Domain model representing a processed charge or refund.

    Notes/Architectural Intent:
        Represents the final financial step of the trip booking workflow.
    """

    model_config = ConfigDict(frozen=True)

    transaction_id: str = Field(default_factory=lambda: f"txn-{uuid4().hex[:8]}")
    customer_id: str
    amount: float
    currency: str = "USD"
    status: BookingStatus = BookingStatus.CONFIRMED


class TripBookingSummary(BaseModel):
    """Aggregated summary of a completed or compensated holiday trip.

    Notes/Architectural Intent:
        Immutable aggregate view returned to client interfaces upon saga completion.
    """

    model_config = ConfigDict(frozen=True)

    trip_id: str
    customer_id: str
    destination: str
    status: BookingStatus
    total_cost: float
    flight: FlightReservation | None = None
    hotel: HotelReservation | None = None
    car: CarReservation | None = None
    payment: PaymentReceipt | None = None
    compensated_steps: list[str] = Field(default_factory=list)
    error_message: str | None = None


__all__ = [
    "BookingStatus",
    "CarReservation",
    "FlightReservation",
    "HotelReservation",
    "PaymentReceipt",
    "TripBookingRequest",
    "TripBookingSummary",
]
