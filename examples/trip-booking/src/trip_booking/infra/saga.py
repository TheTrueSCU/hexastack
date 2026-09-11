"""Distributed saga assembly and execution coordinator for Trip Booking.

Notes/Architectural Intent:
    Assembles the 4-step distributed transaction (Flight -> Hotel -> Car -> Payment)
    using hexastack-cqrs declarative @saga and @step decorators.
    Executes via InMemorySagaOrchestrator and guarantees strict LIFO compensation unwinding on failure.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from hexastack_cqrs.adapters.sagas import InMemorySagaOrchestrator, InMemorySagaStorage
from hexastack_cqrs.domain.sagas import SagaDefinition, SagaStatus
from hexastack_cqrs.infra.decorators import saga, step

from trip_booking.domain.models import (
    BookingStatus,
    CarReservation,
    FlightReservation,
    HotelReservation,
    PaymentReceipt,
    TripBookingRequest,
    TripBookingSummary,
)
from trip_booking.ports.services import (
    CarRentalPort,
    FlightServicePort,
    HotelServicePort,
    PaymentServicePort,
)


@saga(name="TripBookingSaga")
class TripBookingCoordinator:
    """Orchestrator coordinator that binds domain services into a compensable Saga workflow.

    Notes/Architectural Intent:
        Encapsulates saga step sequencing, cross-step state passing, and compensation mapping
        using hexastack-cqrs declarative @saga and @step decorators.
    """

    def __init__(
        self,
        flight_service: FlightServicePort,
        hotel_service: HotelServicePort,
        car_rental_service: CarRentalPort,
        payment_service: PaymentServicePort,
        orchestrator: InMemorySagaOrchestrator | None = None,
    ) -> None:
        self.flight_service = flight_service
        self.hotel_service = hotel_service
        self.car_rental_service = car_rental_service
        self.payment_service = payment_service
        self.orchestrator = orchestrator or InMemorySagaOrchestrator(
            storage=InMemorySagaStorage()
        )

    @step(name="BookFlight", order=1, compensate="cancel_flight")
    def book_flight(self, request: TripBookingRequest) -> FlightReservation:
        """Step 1: Reserve airline flight for requested destination.

        Args:
            request: Customer booking request parameters.

        Returns:
            Confirmed FlightReservation.
        """
        return self.flight_service.book_flight(request)

    def cancel_flight(self, reservation: FlightReservation) -> None:
        """Compensate Step 1: Cancel confirmed airline flight.

        Args:
            reservation: Previously confirmed FlightReservation to cancel.
        """
        self.flight_service.cancel_flight(reservation)

    @step(name="ReserveHotel", order=2, compensate="cancel_hotel")
    def reserve_hotel(self, request: TripBookingRequest) -> HotelReservation:
        """Step 2: Reserve hotel accommodation.

        Args:
            request: Customer booking request parameters.

        Returns:
            Confirmed HotelReservation.
        """
        return self.hotel_service.reserve_hotel(request)

    def cancel_hotel(self, reservation: HotelReservation) -> None:
        """Compensate Step 2: Cancel hotel accommodation.

        Args:
            reservation: Previously confirmed HotelReservation to cancel.
        """
        self.hotel_service.cancel_hotel(reservation)

    @step(name="RentCar", order=3, compensate="cancel_car")
    def rent_car(self, request: TripBookingRequest) -> CarReservation:
        """Step 3: Rent rental vehicle.

        Args:
            request: Customer booking request parameters.

        Returns:
            Confirmed CarReservation.
        """
        return self.car_rental_service.rent_car(request)

    def cancel_car(self, reservation: CarReservation) -> None:
        """Compensate Step 3: Cancel vehicle rental.

        Args:
            reservation: Previously confirmed CarReservation to cancel.
        """
        self.car_rental_service.cancel_car(reservation)

    @step(name="ProcessPayment", order=4, compensate="refund_payment")
    def process_payment(
        self, request: TripBookingRequest, ctx: dict[str, Any]
    ) -> PaymentReceipt:
        """Step 4: Process customer payment based on aggregated reservation costs.

        Args:
            request: Customer booking request parameters.
            ctx: Accumulated saga execution context containing prior step outputs.

        Returns:
            Confirmed PaymentReceipt.
        """
        flight: FlightReservation = ctx["BookFlight"]
        hotel: HotelReservation = ctx["ReserveHotel"]
        car: CarReservation = ctx["RentCar"]
        total_amount = flight.price + hotel.price + car.price
        return self.payment_service.process_payment(request, total_amount)

    def refund_payment(self, receipt: PaymentReceipt) -> None:
        """Compensate Step 4: Issue refund for payment transaction.

        Args:
            receipt: PaymentReceipt to refund.
        """
        self.payment_service.refund_payment(receipt)

    def build_saga(self, context: Any = None) -> SagaDefinition:
        """Construct the 4-step compensable saga definition for the requested trip.

        Args:
            context: Customer booking request parameters.

        Returns:
            Configured SagaDefinition instance.

        Notes/Architectural Intent:
            Dynamically synthesized by @saga decorator from @step declarations.
        """
        raise NotImplementedError("Synthesized by @saga decorator")

    def execute(self, request: TripBookingRequest) -> TripBookingSummary:
        """Execute the trip booking saga synchronously.

        Args:
            request: Customer trip request.

        Returns:
            TripBookingSummary with final status and confirmed or compensated itinerary.
        """
        trip_id = f"trip-{uuid4().hex[:8]}"
        saga_def = self.build_saga(request)
        result = self.orchestrator.execute(saga_def)

        if result.status == SagaStatus.COMPLETED:
            flight: FlightReservation = result.step_results["BookFlight"]
            hotel: HotelReservation = result.step_results["ReserveHotel"]
            car: CarReservation = result.step_results["RentCar"]
            payment: PaymentReceipt = result.step_results["ProcessPayment"]
            return TripBookingSummary(
                trip_id=trip_id,
                customer_id=request.customer_id,
                destination=request.destination,
                status=BookingStatus.CONFIRMED,
                total_cost=payment.amount,
                flight=flight,
                hotel=hotel,
                car=car,
                payment=payment,
                compensated_steps=[],
            )

        # Failure / Compensation occurred
        compensated_steps = result.compensated_steps

        flight_res = result.step_results.get("BookFlight")
        hotel_res = result.step_results.get("ReserveHotel")
        car_res = result.step_results.get("RentCar")
        payment_res = result.step_results.get("ProcessPayment")

        return TripBookingSummary(
            trip_id=trip_id,
            customer_id=request.customer_id,
            destination=request.destination,
            status=BookingStatus.CANCELLED,
            total_cost=0.0,
            flight=flight_res,
            hotel=hotel_res,
            car=car_res,
            payment=payment_res,
            compensated_steps=compensated_steps,
            error_message=result.error,
        )


__all__ = [
    "TripBookingCoordinator",
]
