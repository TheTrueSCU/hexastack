"""In-memory driven adapters for booking partners and payment processing.

Notes/Architectural Intent:
    Simulates external microservices and third-party APIs. Includes failure injection toggles
    to test and demonstrate automated reverse (LIFO) compensation unwinding.
"""

from __future__ import annotations

from trip_booking.domain.models import (
    BookingStatus,
    CarReservation,
    FlightReservation,
    HotelReservation,
    PaymentReceipt,
    TripBookingRequest,
)
from trip_booking.ports.services import (
    CarRentalPort,
    FlightServicePort,
    HotelServicePort,
    PaymentServicePort,
)


class InMemoryFlightService(FlightServicePort):
    """In-memory flight reservation adapter with failure injection."""

    def __init__(self, should_fail: bool = False, flight_cost: float = 450.0) -> None:
        self.should_fail = should_fail
        self.flight_cost = flight_cost
        self.reservations: dict[str, FlightReservation] = {}
        self.cancelled_reservations: list[str] = []

    def book_flight(self, request: TripBookingRequest) -> FlightReservation:
        """Reserve flight with optional failure injection."""
        if self.should_fail:
            raise RuntimeError(
                f"Airline GDS error: No available seats to {request.destination}."
            )

        res = FlightReservation(
            customer_id=request.customer_id,
            flight_number="HX-404",
            destination=request.destination,
            seat="12A",
            price=self.flight_cost,
            status=BookingStatus.CONFIRMED,
        )
        self.reservations[res.reservation_id] = res
        return res

    def cancel_flight(self, reservation: FlightReservation) -> None:
        """Compensate flight booking."""
        self.cancelled_reservations.append(reservation.reservation_id)
        if reservation.reservation_id in self.reservations:
            existing = self.reservations[reservation.reservation_id]
            self.reservations[reservation.reservation_id] = FlightReservation(
                reservation_id=existing.reservation_id,
                customer_id=existing.customer_id,
                flight_number=existing.flight_number,
                destination=existing.destination,
                seat=existing.seat,
                price=existing.price,
                status=BookingStatus.CANCELLED,
            )


class InMemoryHotelService(HotelServicePort):
    """In-memory hotel booking adapter with failure injection."""

    def __init__(self, should_fail: bool = False, nightly_rate: float = 120.0) -> None:
        self.should_fail = should_fail
        self.nightly_rate = nightly_rate
        self.reservations: dict[str, HotelReservation] = {}
        self.cancelled_reservations: list[str] = []

    def reserve_hotel(self, request: TripBookingRequest) -> HotelReservation:
        """Reserve hotel room with optional failure injection."""
        if self.should_fail:
            raise RuntimeError(f"Hotel inventory exhausted in {request.destination}.")

        total_price = self.nightly_rate * request.hotel_nights
        res = HotelReservation(
            customer_id=request.customer_id,
            hotel_name=f"The Grand {request.destination} Hotel",
            destination=request.destination,
            nights=request.hotel_nights,
            price=total_price,
            status=BookingStatus.CONFIRMED,
        )
        self.reservations[res.reservation_id] = res
        return res

    def cancel_hotel(self, reservation: HotelReservation) -> None:
        """Compensate hotel booking."""
        self.cancelled_reservations.append(reservation.reservation_id)
        if reservation.reservation_id in self.reservations:
            existing = self.reservations[reservation.reservation_id]
            self.reservations[reservation.reservation_id] = HotelReservation(
                reservation_id=existing.reservation_id,
                customer_id=existing.customer_id,
                hotel_name=existing.hotel_name,
                destination=existing.destination,
                nights=existing.nights,
                price=existing.price,
                status=BookingStatus.CANCELLED,
            )


class InMemoryCarRentalService(CarRentalPort):
    """In-memory car rental adapter with failure injection."""

    def __init__(self, should_fail: bool = False, daily_rate: float = 55.0) -> None:
        self.should_fail = should_fail
        self.daily_rate = daily_rate
        self.reservations: dict[str, CarReservation] = {}
        self.cancelled_reservations: list[str] = []

    def rent_car(self, request: TripBookingRequest) -> CarReservation:
        """Reserve rental car with optional failure injection."""
        if self.should_fail:
            raise RuntimeError(
                f"No {request.car_class} vehicles available at rental desk."
            )

        total_price = self.daily_rate * request.car_rental_days
        res = CarReservation(
            customer_id=request.customer_id,
            vehicle_class=request.car_class,
            rental_days=request.car_rental_days,
            price=total_price,
            status=BookingStatus.CONFIRMED,
        )
        self.reservations[res.reservation_id] = res
        return res

    def cancel_car(self, reservation: CarReservation) -> None:
        """Compensate car rental."""
        self.cancelled_reservations.append(reservation.reservation_id)
        if reservation.reservation_id in self.reservations:
            existing = self.reservations[reservation.reservation_id]
            self.reservations[reservation.reservation_id] = CarReservation(
                reservation_id=existing.reservation_id,
                customer_id=existing.customer_id,
                vehicle_class=existing.vehicle_class,
                rental_days=existing.rental_days,
                price=existing.price,
                status=BookingStatus.CANCELLED,
            )


class InMemoryPaymentService(PaymentServicePort):
    """In-memory payment processing adapter with failure injection."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.payments: dict[str, PaymentReceipt] = {}
        self.refunded_payments: list[str] = []

    def process_payment(
        self, request: TripBookingRequest, amount: float
    ) -> PaymentReceipt:
        """Process payment charge with optional failure injection."""
        if self.should_fail:
            raise RuntimeError("Payment declined: Insufficient credit line.")

        receipt = PaymentReceipt(
            customer_id=request.customer_id,
            amount=amount,
            status=BookingStatus.CONFIRMED,
        )
        self.payments[receipt.transaction_id] = receipt
        return receipt

    def refund_payment(self, receipt: PaymentReceipt) -> None:
        """Compensate payment transaction with refund."""
        self.refunded_payments.append(receipt.transaction_id)
        if receipt.transaction_id in self.payments:
            existing = self.payments[receipt.transaction_id]
            self.payments[receipt.transaction_id] = PaymentReceipt(
                transaction_id=existing.transaction_id,
                customer_id=existing.customer_id,
                amount=existing.amount,
                currency=existing.currency,
                status=BookingStatus.CANCELLED,
            )


__all__ = [
    "InMemoryCarRentalService",
    "InMemoryFlightService",
    "InMemoryHotelService",
    "InMemoryPaymentService",
]
