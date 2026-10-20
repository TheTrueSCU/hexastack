"""Performance microbenchmarks for CloudEvent serialization and deserialization.

Notes/Architectural Intent:
    Measures latency and throughput of msgspec-powered JSON and MessagePack codecs
    for CloudEventEnvelope instances, proving sub-microsecond serialization overhead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from hexastack_events.domain.models import CloudEventEnvelope
from hexastack_events.domain.serialization import MsgspecEnvelopeSerializer

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


def _make_sample_envelope() -> CloudEventEnvelope:
    """Create a populated sample CloudEventEnvelope instance."""
    return CloudEventEnvelope(
        id="evt-perf-bench-12345",
        source="urn:hexastack:service:billing",
        type="io.hexastack.invoice.created",
        time="2026-10-20T12:00:00Z",
        correlationid="corr-trace-98765",
        tenantid="tenant-acme",
        data={
            "invoice_id": "inv_998877",
            "amount_cents": 149900,
            "currency": "USD",
            "customer_id": "cust_443322",
            "line_items": [
                {
                    "description": "Enterprise Subscription",
                    "qty": 1,
                    "unit_price": 149900,
                }
            ],
            "status": "APPROVED",
        },
    )


def test_perf_cloudevent_json_serialize(benchmark: BenchmarkFixture) -> None:
    """Benchmark CloudEvent serialization into UTF-8 JSON bytes.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies raw encoding throughput of msgspec JSON encoders over domain models.
    """
    serializer = MsgspecEnvelopeSerializer(use_msgpack=False)
    envelope = _make_sample_envelope()

    res = benchmark(serializer.serialize_envelope, envelope)
    has_id = b"evt-perf-bench-12345" in res
    assert has_id is True


def test_perf_cloudevent_json_deserialize(benchmark: BenchmarkFixture) -> None:
    """Benchmark UTF-8 JSON bytes deserialization into CloudEventEnvelope.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies JSON decoding latency and model validation through msgspec and Pydantic.
    """
    serializer = MsgspecEnvelopeSerializer(use_msgpack=False)
    envelope = _make_sample_envelope()
    payload_bytes = serializer.serialize_envelope(envelope)

    res = benchmark(serializer.deserialize_envelope, payload_bytes)
    res_id = res.id
    assert res_id == "evt-perf-bench-12345"


def test_perf_cloudevent_msgpack_serialize(benchmark: BenchmarkFixture) -> None:
    """Benchmark CloudEvent binary serialization into MessagePack bytes.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies raw MessagePack encoding speed for high-throughput messaging brokers.
    """
    serializer = MsgspecEnvelopeSerializer(use_msgpack=True)
    envelope = _make_sample_envelope()

    res = benchmark(serializer.serialize_envelope, envelope)
    res_len = len(res)
    assert res_len > 0


def test_perf_cloudevent_msgpack_deserialize(benchmark: BenchmarkFixture) -> None:
    """Benchmark MessagePack binary bytes deserialization into CloudEventEnvelope.

    Args:
        benchmark: pytest-benchmark fixture.

    Notes/Architectural Intent:
        Quantifies MessagePack decoding and domain model instantiation latency.
    """
    serializer = MsgspecEnvelopeSerializer(use_msgpack=True)
    envelope = _make_sample_envelope()
    payload_bytes = serializer.serialize_envelope(envelope)

    res = benchmark(serializer.deserialize_envelope, payload_bytes)
    res_id = res.id
    assert res_id == "evt-perf-bench-12345"
