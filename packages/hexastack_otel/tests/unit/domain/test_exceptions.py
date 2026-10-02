from hexastack_core.domain.exceptions import HexastackError
from hexastack_otel.domain.exceptions import (
    OtelError,
    TracingConfigurationError,
)


def test_otel_exceptions_hierarchy():
    err = OtelError("Base telemetry error")
    assert isinstance(err, HexastackError)

    cfg_err = TracingConfigurationError("Invalid endpoint")
    assert isinstance(cfg_err, OtelError)
