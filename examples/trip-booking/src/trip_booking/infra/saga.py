"""Distributed saga assembly and execution coordinator for Trip Booking.

Notes/Architectural Intent:
    Assembles the 4-step distributed transaction (Flight -> Hotel -> Car -> Payment)
    using hexastack-cqrs SagaBuilder DSL and executes via InMemorySagaOrchestrator.
    Guarantees strict LIFO compensation unwinding on failure.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from hexastack_cqrs.adapters.sagas import InMemorySagaOrchestrator, InMemorySagaStorage
from hexastack_cqrs.domain.sagas import SagaDefinition, SagaStatus
from hexastack_cqrs.infra.sagas import SagaBuilder

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


class TripBookingCoordinator:
    """Orchestrator coordinator that binds domain services into a compensable Saga workflow.

    Notes/Architectural Intent:
        Encapsulates saga step sequencing, cross-step state passing, and compensation mapping.
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
        self.orchestrator = orchestrator or InMemorySagaOrchestrator(storage=InMemorySagaStorage())

    def build_saga(self, request: TripBookingRequest) -> SagaDefinition:
        """Construct the 4-step compensable saga definition for the requested trip.

        Args:
            request: Customer booking request parameters.

        Returns:
            Configured SagaDefinition instance.
        """
        builder = SagaBuilder(
            name=f"TripBookingSaga-{request.customer_id}",
            description=f"Trip booking to {request.destination} for customer {request.customer_id}",
        )

        # Step 1: Book Flight
        builder.step(
            name="BookFlight",
            action=lambda ctx: self.flight_service.book_flight(request),
            compensate=lambda res, ctx: self.flight_service.cancel_flight(res),
        )

        # Step 2: Reserve Hotel
        builder.step(
            name="ReserveHotel",
            action=lambda ctx: self.hotel_service.reserve_hotel(request),
            compensate=lambda res, ctx: self.hotel_service.cancel_hotel(res),
        )

        # Step 3: Rent Car
        builder.step(
            name="RentCar",
            action=lambda ctx: self.car_rental_service.rent_car(request),
            compensate=lambda res, ctx: self.car_rental_service.cancel_car(res),
        )

        # Step 4: Process Payment (calculates total cost from previous 3 confirmed reservations)
        def _process_payment(ctx: dict[str, Any]) -> PaymentReceipt:
            flight: FlightReservation = ctx["BookFlight"]
            hotel: HotelReservation = ctx["ReserveHotel"]
            car: CarReservation = ctx["RentCar"]
            total_amount = flight.price + hotel.price + car.price
            return self.payment_service.process_payment(request, total_amount)

        def _refund_payment(receipt: PaymentReceipt, ctx: Any = None) -> None:
            self.payment_service.refund_payment(receipt)

        builder.step(
            name="ProcessPayment",
            action=_process_payment,
            compensate=_refund_payment,
        )

        return builder.build()

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
