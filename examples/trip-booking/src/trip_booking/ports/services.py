"""Port interfaces defining booking service and payment boundaries.

Notes/Architectural Intent:
    Abstract ports (Hexagonal secondary boundaries) defining contracts for external
    travel partners and banking services. Decouples domain saga logic from vendor APIs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from trip_booking.domain.models import (
    CarReservation,
    FlightReservation,
    HotelReservation,
    PaymentReceipt,
    TripBookingRequest,
)


class FlightServicePort(ABC):
    """Abstract port for flight reservations and cancellations.

    Notes/Architectural Intent:
        Secondary port representing an external Airline GDS or flight API.
    """

    @abstractmethod
    def book_flight(self, request: TripBookingRequest) -> FlightReservation:
        """Reserve a round-trip flight.

        Args:
            request: Customer trip booking parameters.

        Returns:
            Confirmed FlightReservation domain model.

        Raises:
            Exception: If flight reservation fails or inventory is depleted.
        """

    @abstractmethod
    def cancel_flight(self, reservation: FlightReservation) -> None:
        """Cancel an existing flight reservation (compensating action).

        Args:
            reservation: The reservation to cancel.
        """


class HotelServicePort(ABC):
    """Abstract port for hotel accommodation reservations and cancellations.

    Notes/Architectural Intent:
        Secondary port representing hotel booking providers.
    """

    @abstractmethod
    def reserve_hotel(self, request: TripBookingRequest) -> HotelReservation:
        """Reserve a hotel room.

        Args:
            request: Customer trip booking parameters.

        Returns:
            Confirmed HotelReservation domain model.

        Raises:
            Exception: If hotel booking fails.
        """

    @abstractmethod
    def cancel_hotel(self, reservation: HotelReservation) -> None:
        """Cancel an existing hotel reservation (compensating action).

        Args:
            reservation: The reservation to cancel.
        """


class CarRentalPort(ABC):
    """Abstract port for ground transportation reservations.

    Notes/Architectural Intent:
        Secondary port representing rental car providers.
    """

    @abstractmethod
    def rent_car(self, request: TripBookingRequest) -> CarReservation:
        """Reserve a rental car.

        Args:
            request: Customer trip booking parameters.

        Returns:
            Confirmed CarReservation domain model.

        Raises:
            Exception: If vehicle class unavailable or rental fails.
        """

    @abstractmethod
    def cancel_car(self, reservation: CarReservation) -> None:
        """Cancel an existing car rental (compensating action).

        Args:
            reservation: The reservation to cancel.
        """


class PaymentServicePort(ABC):
    """Abstract port for financial authorization and refunds.

    Notes/Architectural Intent:
        Secondary port representing payment gateways (Stripe, Adyen).
    """

    @abstractmethod
    def process_payment(
        self, request: TripBookingRequest, amount: float
    ) -> PaymentReceipt:
        """Process financial charge for the aggregated trip cost.

        Args:
            request: Customer trip booking parameters.
            amount: Total monetary amount to charge.

        Returns:
            PaymentReceipt domain model.

        Raises:
            Exception: If credit card charge fails or funds are insufficient.
        """

    @abstractmethod
    def refund_payment(self, receipt: PaymentReceipt) -> None:
        """Refund an already charged transaction (compensating action).

        Args:
            receipt: The transaction receipt to refund.
        """


__all__ = [
    "CarRentalPort",
    "FlightServicePort",
    "HotelServicePort",
    "PaymentServicePort",
]
