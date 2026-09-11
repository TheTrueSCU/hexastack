"""FastAPI HTTP driving adapter for Trip Booking Saga execution.

Notes/Architectural Intent:
    Provides HTTP REST endpoints to initiate distributed trip booking sagas.
    Supports interactive fault injection via query parameters to demonstrate LIFO compensations.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, FastAPI, Query, Response

from trip_booking.domain.models import (
    BookingStatus,
    TripBookingRequest,
    TripBookingSummary,
)
from trip_booking.infra.bootstrap import TripBookingServiceContainer, create_container


def get_default_container() -> TripBookingServiceContainer:
    """Dependency provider for the default service container."""
    return create_container()


def create_api_router(container_override: TripBookingServiceContainer | None = None) -> APIRouter:
    """Create configured FastAPI APIRouter for trip booking operations."""
    router = APIRouter(prefix="/trips", tags=["trips"])

    @router.get("/health", summary="Health check")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "trip-booking"}

    @router.post(
        "/book",
        response_model=TripBookingSummary,
        summary="Book a complete holiday trip via Distributed Saga",
    )
    def book_trip(
        request: TripBookingRequest,
        response: Response,
        fail_at: Annotated[
            Literal["flight", "hotel", "car", "payment"] | None,
            Query(description="Optionally inject failure into a specific step to trigger compensation"),
        ] = None,
        container: Annotated[TripBookingServiceContainer | None, Depends(get_default_container)] = None,
    ) -> TripBookingSummary:
        active_container = container_override or container or get_default_container()
        if fail_at is not None:
            active_container = create_container(
                fail_flight=(fail_at == "flight"),
                fail_hotel=(fail_at == "hotel"),
                fail_car=(fail_at == "car"),
                fail_payment=(fail_at == "payment"),
            )

        summary = active_container.coordinator.execute(request)
        if summary.status == BookingStatus.CANCELLED:
            response.status_code = 422

        return summary

    return router


def create_app(container: TripBookingServiceContainer | None = None) -> FastAPI:
    """Construct and configure the complete FastAPI ASGI application."""
    app = FastAPI(
        title="Trip Booking Service",
        description="Flagship Distributed Saga Orchestration Reference Application powered by Hexastack",
        version="0.1.0",
    )
    app.include_router(create_api_router(container))
    return app


__all__ = [
    "create_api_router",
    "create_app",
]
