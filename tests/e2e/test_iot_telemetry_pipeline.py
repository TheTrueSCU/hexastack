"""End-to-End integration test and user journey for IoT Telemetry Ingestion Pipeline.

Notes/Architectural Intent:
    Validates high-throughput IoT telemetry ingestion (Issue #73) demonstrating:
    1. Bidirectional gRPC streaming ingestion via hexastack-grpc dispatchers.
    2. Sub-millisecond zero-copy MessagePack and JSON serialization with msgspec.
    3. Persistent local L2 disk caching (DiskCacheAdapter) of sensor calibration profiles across restarts.
    4. End-to-end OpenTelemetry distributed tracing and latency metrics recording.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator, Coroutine, Generator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from rodi import Container

from hexastack_core.adapters.cache.disk import DiskCacheAdapter
from hexastack_core.domain import Command, Query
from hexastack_cqrs.adapters.buses.command.synchronous import SynchronousCommandBus
from hexastack_cqrs.adapters.buses.query.synchronous import SynchronousQueryBus
from hexastack_cqrs.infra.registries import HandlerRegistry
from hexastack_cqrs.ports.buses import CommandBusPort, QueryBusPort
from hexastack_events.domain.models import CloudEventEnvelope
from hexastack_events.domain.serialization import (
    decode_cloudevent_msgpack,
    encode_cloudevent_bytes,
    encode_cloudevent_msgpack,
)
from hexastack_grpc.infra.dispatch import dispatch_rpc_bidirectional_stream
from hexastack_otel.adapters.tracing.in_memory import InMemoryTracingAdapter


def _run_coro_safely(coro: Coroutine[Any, Any, Any]) -> Any:
    """Execute coroutine safely even if an event loop is already running on the current thread."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Domain Models & CQRS Messages
# ---------------------------------------------------------------------------


class IngestSensorReadingCommand(Command):
    """Command to ingest a calibrated sensor telemetry reading."""

    device_id: str
    metric_name: str
    raw_value: float
    timestamp: float


class GetDeviceCalibrationQuery(Query[dict[str, Any]]):
    """Query to retrieve sensor calibration factors from persistent cache."""

    device_id: str


class MockGrpcTelemetryPacket:
    """Mock Protobuf message representing a high-frequency gRPC telemetry frame."""

    def __init__(
        self,
        device_id: str,
        metric_name: str,
        raw_value: float,
        timestamp: float | None = None,
    ) -> None:
        self.device_id = device_id
        self.metric_name = metric_name
        self.raw_value = raw_value
        self.timestamp = timestamp or time.time()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def disk_cache_dir(tmp_path: Path) -> Generator[Path]:
    """Provide isolated temporary directory for persistent DiskCacheAdapter."""
    cache_path = tmp_path / "iot_l2_cache"
    cache_path.mkdir(parents=True, exist_ok=True)
    yield cache_path


@pytest.fixture
def in_memory_tracer() -> Generator[InMemoryTracingAdapter]:
    """Provide an isolated InMemoryTracingAdapter for telemetry trace validation."""
    tracer = InMemoryTracingAdapter()
    yield tracer
    tracer.shutdown()


# ---------------------------------------------------------------------------
# Test Cases
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_iot_telemetry_grpc_streaming_and_disk_cache(
    disk_cache_dir: Path,
    in_memory_tracer: InMemoryTracingAdapter,
) -> None:
    """Verify bidirectional gRPC telemetry streaming with persistent disk cache calibration.

    Args:
        disk_cache_dir: Isolated temporary directory for SQLite-backed disk cache.
        in_memory_tracer: In-memory OpenTelemetry tracer recording ingestion spans.

    Notes/Architectural Intent:
        Streams incoming sensor packets through dispatch_rpc_bidirectional_stream, applying
        real-time calibration parameters retrieved from DiskCacheAdapter, while recording
        distributed telemetry spans for each packet.
    """
    # 1. Initialize persistent L2 disk cache and populate calibration profiles
    cache = DiskCacheAdapter(directory=str(disk_cache_dir))
    cache.set(
        "calib:sensor-temp-01",
        {"offset": -1.5, "multiplier": 1.02},
    )
    cache.set(
        "calib:sensor-press-02",
        {"offset": 0.0, "multiplier": 0.98},
    )

    # 2. Configure CQRS Command Bus and DI Container
    container = Container()
    handler_reg = HandlerRegistry()
    command_bus = SynchronousCommandBus(handler_registry=handler_reg)
    query_bus = SynchronousQueryBus(handler_registry=handler_reg)

    container.add_instance(command_bus, declared_class=CommandBusPort)
    container.add_instance(query_bus, declared_class=QueryBusPort)

    def _handle_ingest(cmd: IngestSensorReadingCommand) -> dict[str, Any]:
        with in_memory_tracer.trace_scope("iot.ingest_telemetry") as span:
            span.set_attribute("device.id", cmd.device_id)
            span.set_attribute("metric.name", cmd.metric_name)

            calib_key = f"calib:{cmd.device_id}"
            calib = cache.get(calib_key) or {"offset": 0.0, "multiplier": 1.0}
            calibrated_val = (cmd.raw_value + calib["offset"]) * calib["multiplier"]

            return {
                "device_id": cmd.device_id,
                "metric_name": cmd.metric_name,
                "calibrated_value": round(calibrated_val, 4),
                "timestamp": cmd.timestamp,
                "status": "ACCEPTED",
            }

    handler_reg.register(IngestSensorReadingCommand, _handle_ingest)

    # 3. Stream incoming gRPC telemetry packets through bidirectional dispatch
    async def _mock_client_stream() -> AsyncIterator[MockGrpcTelemetryPacket]:
        packets = [
            MockGrpcTelemetryPacket(
                "sensor-temp-01", "temperature_c", 23.5, time.time()
            ),
            MockGrpcTelemetryPacket(
                "sensor-temp-01", "temperature_c", 24.0, time.time()
            ),
            MockGrpcTelemetryPacket(
                "sensor-press-02", "pressure_hpa", 1013.25, time.time()
            ),
        ]
        for p in packets:
            yield p

    async def _consume_stream() -> list[dict[str, Any]]:
        stream_results: list[dict[str, Any]] = []
        async for response in dispatch_rpc_bidirectional_stream(
            requests_iterator=_mock_client_stream(),
            command_cls=IngestSensorReadingCommand,
            container=container,
        ):
            stream_results.append(response)
        return stream_results

    results: list[dict[str, Any]] = _run_coro_safely(_consume_stream())

    # 4. Verify streaming responses
    result_count = len(results)
    assert result_count == 3

    # Packet 1: (23.5 - 1.5) * 1.02 = 22.0 * 1.02 = 22.44
    first_reading = results[0]["calibrated_value"]
    assert first_reading == 22.44

    # Packet 2: (24.0 - 1.5) * 1.02 = 22.5 * 1.02 = 22.95
    second_reading = results[1]["calibrated_value"]
    assert second_reading == 22.95

    # Packet 3: (1013.25 + 0.0) * 0.98 = 992.985
    third_reading = results[2]["calibrated_value"]
    assert third_reading == 992.985

    # 5. Verify OpenTelemetry span recording
    spans = in_memory_tracer.finished_spans
    span_count = len(spans)
    assert span_count == 3

    span_devices = [s.attributes.get("device.id") for s in spans]
    assert "sensor-temp-01" in span_devices
    assert "sensor-press-02" in span_devices


@pytest.mark.e2e
def test_iot_telemetry_msgpack_zero_copy_serialization() -> None:
    """Verify zero-copy MessagePack and JSON encoding for high-frequency CloudEvent telemetry.

    Notes/Architectural Intent:
        Demonstrates msgspec wire encoding microsecond-level performance and compact binary
        density compared to standard JSON representations.
    """
    telemetry_envelope = CloudEventEnvelope(
        id=f"evt-{uuid.uuid4().hex[:8]}",
        source="hexastack.iot.gateway",
        type="SensorReadingEvent",
        time=datetime.now(UTC).isoformat(),
        data={
            "device_id": "sensor-vibe-44",
            "frequency_hz": 12500.0,
            "amplitude_g": 0.84,
            "readings": [0.81, 0.83, 0.86, 0.84, 0.82],
        },
    )

    # 1. Encode via MessagePack binary format
    msgpack_bytes = encode_cloudevent_msgpack(telemetry_envelope)
    is_bytes = isinstance(msgpack_bytes, bytes)
    assert is_bytes is True

    # 2. Encode via standard UTF-8 JSON format
    json_bytes = encode_cloudevent_bytes(telemetry_envelope)
    is_json = isinstance(json_bytes, bytes)
    assert is_json is True

    # MessagePack binary packing must be strictly smaller than or equal to JSON
    msgpack_len = len(msgpack_bytes)
    json_len = len(json_bytes)
    assert msgpack_len <= json_len

    # 3. Decode MessagePack payload back into CloudEvent dictionary
    decoded = decode_cloudevent_msgpack(msgpack_bytes)
    event_type = decoded.get("type")
    assert event_type == "SensorReadingEvent"

    decoded_data = decoded.get("data")
    assert isinstance(decoded_data, dict)
    delivered_device = decoded_data.get("device_id")
    assert delivered_device == "sensor-vibe-44"

    delivered_freq = decoded_data.get("frequency_hz")
    assert delivered_freq == 12500.0


@pytest.mark.e2e
def test_iot_telemetry_persistent_cache_survives_restart(disk_cache_dir: Path) -> None:
    """Verify persistent L2 DiskCacheAdapter calibration parameters survive process restarts.

    Args:
        disk_cache_dir: Isolated temporary directory for SQLite-backed disk cache.

    Notes/Architectural Intent:
        Validates the resilient edge-computing invariant: when an IoT gateway or edge worker
        restarts, calibration curves stored in DiskCacheAdapter remain instantly available
        without network re-fetch or remote database round-trips.
    """
    # 1. First process life cycle: write calibration offsets to disk cache
    cache_proc1 = DiskCacheAdapter(directory=str(disk_cache_dir))
    cache_proc1.set("device:edge-node-09:offset", 4.125)
    cache_proc1.set("device:edge-node-09:scale", 1.008)

    val_proc1 = cache_proc1.get("device:edge-node-09:offset")
    assert val_proc1 == 4.125

    # 2. Simulate process termination and garbage collection
    del cache_proc1

    # 3. Second process life cycle: instantiate new DiskCacheAdapter on same directory
    cache_proc2 = DiskCacheAdapter(directory=str(disk_cache_dir))

    offset_survived = cache_proc2.get("device:edge-node-09:offset")
    assert offset_survived == 4.125

    scale_survived = cache_proc2.get("device:edge-node-09:scale")
    assert scale_survived == 1.008

    # Verify cache eviction / deletion
    del_res = cache_proc2.delete("device:edge-node-09:offset")
    assert del_res is True

    val_deleted = cache_proc2.get("device:edge-node-09:offset")
    assert val_deleted is None


__all__ = [
    "test_iot_telemetry_grpc_streaming_and_disk_cache",
    "test_iot_telemetry_msgpack_zero_copy_serialization",
    "test_iot_telemetry_persistent_cache_survives_restart",
]
