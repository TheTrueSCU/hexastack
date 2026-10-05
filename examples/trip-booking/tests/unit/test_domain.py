"""Unit tests for domain models and value objects."""

from trip_booking.domain.models import (
    BookingStatus,
    CarReservation,
    FlightReservation,
    HotelReservation,
    PaymentReceipt,
    TripBookingRequest,
    TripBookingSummary,
)


def test_domain_models_creation(sample_request: TripBookingRequest) -> None:
    """Verify initialization and validation of core domain models."""
    cust_id = sample_request.customer_id
    assert cust_id == "cust-101"

    flight = FlightReservation(
        customer_id="cust-101",
        flight_number="HX-100",
        destination="Paris",
        seat="14C",
        price=350.0,
    )
    res_id = flight.reservation_id
    assert res_id.startswith("flt-")
    status = flight.status
    assert status == BookingStatus.CONFIRMED

    hotel = HotelReservation(
        customer_id="cust-101",
        hotel_name="Hotel Paris",
        destination="Paris",
        nights=3,
        price=360.0,
    )
    hotel_status = hotel.status
    assert hotel_status == BookingStatus.CONFIRMED

    car = CarReservation(
        customer_id="cust-101",
        vehicle_class="Sedan",
        rental_days=3,
        price=150.0,
    )
    car_status = car.status
    assert car_status == BookingStatus.CONFIRMED

    payment = PaymentReceipt(
        customer_id="cust-101",
        amount=860.0,
    )
    payment_status = payment.status
    assert payment_status == BookingStatus.CONFIRMED

    summary = TripBookingSummary(
        trip_id="trip-123",
        customer_id="cust-101",
        destination="Paris",
        status=BookingStatus.CONFIRMED,
        total_cost=860.0,
        flight=flight,
        hotel=hotel,
        car=car,
        payment=payment,
    )
    summary_status = summary.status
    assert summary_status == BookingStatus.CONFIRMED
    cost = summary.total_cost
    assert cost == 860.0
