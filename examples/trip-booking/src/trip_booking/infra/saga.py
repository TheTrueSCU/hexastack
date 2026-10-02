"""Distributed saga assembly and execution coordinator for Trip Booking.

Notes/Architectural Intent:
    Assembles the 4-step distributed transaction (Flight -> Hotel -> Car -> Payment)
    as a hexaflow Workflow DAG with automated reverse (LIFO) compensation unwinding on failure.
    Demonstrates how workflows natively subsume the Saga pattern.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from hexaflow import StepContext, Workflow, WorkflowStatus

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
    """Workflow coordinator that binds domain services into a compensable trip booking workflow.

    Notes/Architectural Intent:
        Encapsulates saga step sequencing, cross-step state passing, and compensation mapping
        using hexaflow DAG workflows with reverse (LIFO) compensation unwinding on failure.
    """

    def __init__(
        self,
        flight_service: FlightServicePort,
        hotel_service: HotelServicePort,
        car_rental_service: CarRentalPort,
        payment_service: PaymentServicePort,
    ) -> None:
        self.flight_service = flight_service
        self.hotel_service = hotel_service
        self.car_rental_service = car_rental_service
        self.payment_service = payment_service

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

    def process_payment(
        self, request: TripBookingRequest, ctx: dict[str, Any]
    ) -> PaymentReceipt:
        """Step 4: Process customer payment based on aggregated reservation costs.

        Args:
            request: Customer booking request parameters.
            ctx: Accumulated execution context containing prior step outputs.

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

    def execute(self, request: TripBookingRequest) -> TripBookingSummary:
        """Execute the trip booking workflow synchronously with LIFO compensation unwinding.

        Args:
            request: Customer trip request.

        Returns:
            TripBookingSummary with final status and confirmed or compensated itinerary.
        """
        trip_id = f"trip-{uuid4().hex[:8]}"
        wf = Workflow("TripBookingWorkflow")
        step_outputs: dict[str, Any] = {}
        compensated_steps: list[str] = []

        def _cancel_flight() -> None:
            compensated_steps.append("BookFlight")
            flight_res = step_outputs.get("BookFlight")
            if flight_res is not None:
                self.cancel_flight(flight_res)

        def _cancel_hotel() -> None:
            compensated_steps.append("ReserveHotel")
            hotel_res = step_outputs.get("ReserveHotel")
            if hotel_res is not None:
                self.cancel_hotel(hotel_res)

        def _cancel_car() -> None:
            compensated_steps.append("RentCar")
            car_res = step_outputs.get("RentCar")
            if car_res is not None:
                self.cancel_car(car_res)

        def _refund_payment() -> None:
            compensated_steps.append("ProcessPayment")
            payment_res = step_outputs.get("ProcessPayment")
            if payment_res is not None:
                self.refund_payment(payment_res)

        @wf.step(name="BookFlight", compensation=_cancel_flight)
        def _step_flight(ctx: StepContext) -> FlightReservation:
            res = self.book_flight(request)
            step_outputs["BookFlight"] = res
            return res

        @wf.step(
            name="ReserveHotel",
            depends_on=["BookFlight"],
            compensation=_cancel_hotel,
        )
        def _step_hotel(ctx: StepContext) -> HotelReservation:
            res = self.reserve_hotel(request)
            step_outputs["ReserveHotel"] = res
            return res

        @wf.step(
            name="RentCar",
            depends_on=["ReserveHotel"],
            compensation=_cancel_car,
        )
        def _step_car(ctx: StepContext) -> CarReservation:
            res = self.rent_car(request)
            step_outputs["RentCar"] = res
            return res

        @wf.step(
            name="ProcessPayment",
            depends_on=["RentCar"],
            compensation=_refund_payment,
        )
        def _step_payment(ctx: StepContext) -> PaymentReceipt:
            res = self.process_payment(request, step_outputs)
            step_outputs["ProcessPayment"] = res
            return res

        state = wf.run()

        if state.status == WorkflowStatus.COMPLETED:
            flight: FlightReservation = step_outputs["BookFlight"]
            hotel: HotelReservation = step_outputs["ReserveHotel"]
            car: CarReservation = step_outputs["RentCar"]
            payment: PaymentReceipt = step_outputs["ProcessPayment"]
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

        # Failure occurred -> abort unwinds all completed steps in reverse LIFO order
        wf.abort(state.run_id)

        error_msg = state.error_summary
        for cp in state.step_checkpoints.values():
            if cp.error_traceback and not error_msg:
                error_msg = cp.error_traceback

        flight_res = step_outputs.get("BookFlight")
        hotel_res = step_outputs.get("ReserveHotel")
        car_res = step_outputs.get("RentCar")
        payment_res = step_outputs.get("ProcessPayment")

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
            error_message=error_msg,
        )


__all__ = [
    "TripBookingCoordinator",
]
