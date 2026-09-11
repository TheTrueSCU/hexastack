"""Unit tests for TripBookingCoordinator saga execution and LIFO compensations."""

from trip_booking.domain.models import BookingStatus, TripBookingRequest
from trip_booking.infra.bootstrap import create_container


def test_saga_happy_path(sample_request: TripBookingRequest) -> None:
    """Verify complete forward execution of all 4 booking steps without errors."""
    container = create_container()
    summary = container.coordinator.execute(sample_request)

    status = summary.status
    assert status == BookingStatus.CONFIRMED
    assert summary.flight is not None
    assert summary.hotel is not None
    assert summary.car is not None
    assert summary.payment is not None

    expected_total = summary.flight.price + summary.hotel.price + summary.car.price
    cost = summary.total_cost
    assert cost == expected_total
    comp_steps = summary.compensated_steps
    assert comp_steps == []
    error = summary.error_message
    assert error is None


def test_saga_failure_at_flight_step(sample_request: TripBookingRequest) -> None:
    """Verify that failure on Step 1 (Flight) results in CANCELLED status with zero compensations."""
    container = create_container(fail_flight=True)
    summary = container.coordinator.execute(sample_request)

    status = summary.status
    assert status == BookingStatus.CANCELLED
    error = summary.error_message
    assert error is not None
    assert "Airline GDS error" in error
    comp_steps = summary.compensated_steps
    assert comp_steps == []


def test_saga_failure_at_hotel_step_compensates_flight(
    sample_request: TripBookingRequest,
) -> None:
    """Verify that failure on Step 2 (Hotel) unwinds Step 1 (Flight)."""
    container = create_container(fail_hotel=True)
    summary = container.coordinator.execute(sample_request)

    status = summary.status
    assert status == BookingStatus.CANCELLED
    error = summary.error_message
    assert error is not None
    assert "Hotel inventory exhausted" in error
    comp_steps = summary.compensated_steps
    assert comp_steps == ["BookFlight"]

    flight_cancelled = len(container.flight_service.cancelled_reservations)
    assert flight_cancelled == 1


def test_saga_failure_at_car_rental_step_compensates_hotel_then_flight(
    sample_request: TripBookingRequest,
) -> None:
    """Verify that failure on Step 3 (Car) unwinds Hotel and Flight in strict LIFO order."""
    container = create_container(fail_car=True)
    summary = container.coordinator.execute(sample_request)

    status = summary.status
    assert status == BookingStatus.CANCELLED
    error = summary.error_message
    assert error is not None
    assert "No Compact vehicles available" in error

    # Strict reverse (LIFO) compensation ordering!
    comp_steps = summary.compensated_steps
    assert comp_steps == ["ReserveHotel", "BookFlight"]

    hotel_cancelled = len(container.hotel_service.cancelled_reservations)
    assert hotel_cancelled == 1
    flight_cancelled = len(container.flight_service.cancelled_reservations)
    assert flight_cancelled == 1


def test_saga_failure_at_payment_step_compensates_car_hotel_flight(
    sample_request: TripBookingRequest,
) -> None:
    """Verify that failure on Step 4 (Payment) unwinds Car, Hotel, and Flight in strict LIFO order."""
    container = create_container(fail_payment=True)
    summary = container.coordinator.execute(sample_request)

    status = summary.status
    assert status == BookingStatus.CANCELLED
    error = summary.error_message
    assert error is not None
    assert "Payment declined" in error

    # Strict reverse (LIFO) compensation ordering!
    comp_steps = summary.compensated_steps
    assert comp_steps == ["RentCar", "ReserveHotel", "BookFlight"]

    car_cancelled = len(container.car_service.cancelled_reservations)
    assert car_cancelled == 1
    hotel_cancelled = len(container.hotel_service.cancelled_reservations)
    assert hotel_cancelled == 1
    flight_cancelled = len(container.flight_service.cancelled_reservations)
    assert flight_cancelled == 1
