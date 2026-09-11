"""Pytest configuration and fixtures for Trip Booking reference tests."""

from __future__ import annotations

import pytest

from trip_booking.domain.models import TripBookingRequest
from trip_booking.infra.bootstrap import TripBookingServiceContainer, create_container


@pytest.fixture
def sample_request() -> TripBookingRequest:
    """Provide standard sample booking request."""
    return TripBookingRequest(
        customer_id="cust-101",
        customer_email="alice@example.com",
        destination="Paris",
        departure_date="2026-11-01",
        return_date="2026-11-05",
        hotel_nights=4,
        car_rental_days=4,
        car_class="Compact",
    )


@pytest.fixture
def container() -> TripBookingServiceContainer:
    """Provide default wired in-memory container."""
    return create_container()
