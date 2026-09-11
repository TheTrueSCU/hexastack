"""Unit tests for driven in-memory booking adapters."""

import pytest

from trip_booking.adapters.driven.in_memory import (
    InMemoryCarRentalService,
    InMemoryFlightService,
    InMemoryHotelService,
    InMemoryPaymentService,
)
from trip_booking.domain.models import BookingStatus, TripBookingRequest


def test_flight_adapter_booking_and_cancellation(sample_request: TripBookingRequest) -> None:
    """Verify flight service reservations and compensation cancellation."""
    service = InMemoryFlightService()
    flight = service.book_flight(sample_request)

    res_id = flight.reservation_id
    assert res_id in service.reservations
    status = flight.status
    assert status == BookingStatus.CONFIRMED

    service.cancel_flight(flight)
    cancelled = service.cancelled_reservations
    assert res_id in cancelled
    updated_status = service.reservations[res_id].status
    assert updated_status == BookingStatus.CANCELLED


def test_flight_adapter_failure_injection(sample_request: TripBookingRequest) -> None:
    """Verify flight service raises on injected failure."""
    service = InMemoryFlightService(should_fail=True)
    with pytest.raises(RuntimeError, match="Airline GDS error"):
        service.book_flight(sample_request)


def test_hotel_adapter_booking_and_cancellation(sample_request: TripBookingRequest) -> None:
    """Verify hotel service reservations and compensation cancellation."""
    service = InMemoryHotelService()
    hotel = service.reserve_hotel(sample_request)

    res_id = hotel.reservation_id
    assert res_id in service.reservations
    status = hotel.status
    assert status == BookingStatus.CONFIRMED

    service.cancel_hotel(hotel)
    cancelled = service.cancelled_reservations
    assert res_id in cancelled
    updated_status = service.reservations[res_id].status
    assert updated_status == BookingStatus.CANCELLED


def test_hotel_adapter_failure_injection(sample_request: TripBookingRequest) -> None:
    """Verify hotel service raises on injected failure."""
    service = InMemoryHotelService(should_fail=True)
    with pytest.raises(RuntimeError, match="Hotel inventory exhausted"):
        service.reserve_hotel(sample_request)


def test_car_rental_adapter_booking_and_cancellation(sample_request: TripBookingRequest) -> None:
    """Verify car rental service reservations and compensation cancellation."""
    service = InMemoryCarRentalService()
    car = service.rent_car(sample_request)

    res_id = car.reservation_id
    assert res_id in service.reservations
    status = car.status
    assert status == BookingStatus.CONFIRMED

    service.cancel_car(car)
    cancelled = service.cancelled_reservations
    assert res_id in cancelled
    updated_status = service.reservations[res_id].status
    assert updated_status == BookingStatus.CANCELLED


def test_car_rental_adapter_failure_injection(sample_request: TripBookingRequest) -> None:
    """Verify car rental service raises on injected failure."""
    service = InMemoryCarRentalService(should_fail=True)
    with pytest.raises(RuntimeError, match="No Compact vehicles available"):
        service.rent_car(sample_request)


def test_payment_adapter_charge_and_refund(sample_request: TripBookingRequest) -> None:
    """Verify payment charge and compensation refund."""
    service = InMemoryPaymentService()
    payment = service.process_payment(sample_request, 750.0)

    txn_id = payment.transaction_id
    assert txn_id in service.payments
    status = payment.status
    assert status == BookingStatus.CONFIRMED

    service.refund_payment(payment)
    refunded = service.refunded_payments
    assert txn_id in refunded
    updated_status = service.payments[txn_id].status
    assert updated_status == BookingStatus.CANCELLED


def test_payment_adapter_failure_injection(sample_request: TripBookingRequest) -> None:
    """Verify payment service raises on injected failure."""
    service = InMemoryPaymentService(should_fail=True)
    with pytest.raises(RuntimeError, match="Payment declined"):
        service.process_payment(sample_request, 500.0)
