"""Unit tests for FastAPI driving adapter."""

from fastapi.testclient import TestClient

from trip_booking.adapters.driving.http import create_app
from trip_booking.domain.models import TripBookingRequest


def test_api_health() -> None:
    """Verify health check endpoint."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/trips/health")
    code = response.status_code
    assert code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_api_book_trip_success(sample_request: TripBookingRequest) -> None:
    """Verify HTTP booking on happy path."""
    app = create_app()
    client = TestClient(app)
    response = client.post("/trips/book", json=sample_request.model_dump())
    code = response.status_code
    assert code == 200
    data = response.json()
    assert data["status"] == "CONFIRMED"
    assert data["total_cost"] > 0
    assert data["flight"] is not None
    assert data["hotel"] is not None
    assert data["car"] is not None
    assert data["payment"] is not None


def test_api_book_trip_failure_injection(sample_request: TripBookingRequest) -> None:
    """Verify HTTP booking with injected failure triggers 422 with compensation audit."""
    app = create_app()
    client = TestClient(app)
    response = client.post("/trips/book?fail_at=car", json=sample_request.model_dump())
    code = response.status_code
    assert code == 422
    data = response.json()
    assert data["status"] == "CANCELLED"
    comp_steps = data["compensated_steps"]
    assert comp_steps == ["ReserveHotel", "BookFlight"]
    error = data["error_message"]
    assert "No Compact vehicles available" in error
