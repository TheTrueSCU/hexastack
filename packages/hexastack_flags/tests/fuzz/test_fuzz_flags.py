"""Atheris coverage-guided and adversarial fuzz harness for feature flag evaluation.

Notes/Architectural Intent:
    Stress tests OpenFeatureFlagAdapter and HexastackFlagsConfig against
    pathological JSON structures, malformed context attributes, boundary numbers,
    and corrupted unicode keys to verify total crash resilience and safe fallback behavior.
"""

from __future__ import annotations

import contextlib
import importlib
import json
import random
import sys
import time
from typing import Any

from openfeature import api
from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_flags.adapters.openfeature import OpenFeatureFlagAdapter
from hexastack_flags.domain.config import HexastackFlagsConfig
from hexastack_flags.domain.models import FeatureFlagProviderType, FlagProviderOptions

try:
    atheris: Any = importlib.import_module("atheris")
except ImportError:
    atheris = None

_MAX_PER_CALL_DURATION = 0.05  # 50ms

# Initialize in-memory provider with baseline flags
_flags = {
    "beta-feature": InMemoryFlag(
        default_variant="on",
        variants={"on": True, "off": False},
    ),
    "rate-limit-tier": InMemoryFlag(
        default_variant="standard",
        variants={"standard": 100, "premium": 500},
    ),
    "pricing-multiplier": InMemoryFlag(
        default_variant="base",
        variants={"base": 1.25, "discount": 0.95},
    ),
    "ui-theme": InMemoryFlag(
        default_variant="dark",
        variants={"dark": "dracula", "light": "latte"},
    ),
    "config-map": InMemoryFlag(
        default_variant="v1",
        variants={"v1": {"max_retries": 3, "timeout": 30}},
    ),
}
_provider = InMemoryProvider(_flags)
api.set_provider(_provider)
_adapter = OpenFeatureFlagAdapter()


def fuzz_one_input(data: bytes) -> None:
    """Execute one fuzzed input against flag evaluations and configuration schemas.

    Args:
        data: Arbitrary byte sequence from libFuzzer or random generator.
    """
    if not data:
        return

    # Derive arbitrary string key and payload
    key = ""
    payload: Any = None
    try:
        text = data.decode("utf-8", errors="ignore")
        if text.startswith("{") and text.endswith("}"):
            payload = json.loads(text)
            if isinstance(payload, dict):
                key = str(payload.get("key", text[:20]))
            else:
                key = text[:20]
        else:
            key = text[:30]
            payload = {"raw_len": len(data), "mod": len(data) % 7}
    except Exception:
        key = "fuzz-fallback-key"
        payload = {}

    t0 = time.perf_counter()

    # 1. Fuzz HexastackFlagsConfig & FlagProviderOptions parsing
    if isinstance(payload, dict):
        with contextlib.suppress(Exception):
            _ = HexastackFlagsConfig.model_validate(payload)

        with contextlib.suppress(Exception):
            _ = FlagProviderOptions.model_validate(payload)

    # 2. Build arbitrary EvaluationContext
    attributes = payload if isinstance(payload, dict) else {"val": str(payload)}
    eval_ctx = EvaluationContext(
        targeting_key=key,
        attributes=attributes,
    )

    # 3. Fuzz flag evaluations across all supported value types
    try:
        bool_val = _adapter.get_boolean_value(key, default=False, context=eval_ctx)
        bool_ok = isinstance(bool_val, bool)
        assert bool_ok is True

        str_val = _adapter.get_string_value(key, default="fallback", context=eval_ctx)
        str_ok = isinstance(str_val, str)
        assert str_ok is True

        int_val = _adapter.get_integer_value(key, default=-1, context=eval_ctx)
        int_ok = isinstance(int_val, int)
        assert int_ok is True

        float_val = _adapter.get_float_value(key, default=-1.0, context=eval_ctx)
        float_ok = isinstance(float_val, (float, int))
        assert float_ok is True

        obj_val = _adapter.get_object_value(
            key, default={"default": True}, context=eval_ctx
        )
        obj_ok = obj_val is not None
        assert obj_ok is True

        # Check introspected flags map
        all_flags = _adapter.get_all_flags()
        flags_is_dict = isinstance(all_flags, dict)
        assert flags_is_dict is True

    except AssertionError:
        raise
    except Exception as exc:
        raise AssertionError(
            f"Unexpected uncontained exception during flag evaluation: {type(exc).__name__}: {exc}"
        ) from exc

    elapsed = time.perf_counter() - t0
    if elapsed > _MAX_PER_CALL_DURATION:
        raise TimeoutError(
            f"Flag evaluation processing took {elapsed:.4f}s (> {_MAX_PER_CALL_DURATION}s)"
        )


def test_fuzz_flags_smoke() -> None:
    """Smoke test feature flag fuzz harness under pytest."""
    res = run_standalone(runs=25)
    passed = res["passed"]
    assert passed is True


def run_standalone(runs: int = 100) -> dict[str, Any]:
    """Execute standalone fuzzing loop without requiring native libFuzzer.

    Args:
        runs: Number of random iterations to execute.

    Returns:
        Summary dictionary with execution telemetry.
    """
    start = time.perf_counter()
    passed = 0
    rng = random.Random(42)  # noqa: S311

    known_keys = [
        "beta-feature",
        "rate-limit-tier",
        "pricing-multiplier",
        "ui-theme",
        "config-map",
        "missing-flag",
    ]

    for i in range(runs):
        choice = i % 5
        if choice == 0:
            # Valid known flag with fuzzed context
            payload = json.dumps(
                {
                    "key": known_keys[i % len(known_keys)],
                    "user_id": f"usr_{i}",
                    "tenant": f"org_{i % 3}",
                    "score": i * 1.5,
                }
            ).encode()
        elif choice == 1:
            # Corrupted / invalid configuration dict
            payload = json.dumps(
                {
                    "provider": FeatureFlagProviderType.IN_MEMORY.value,
                    "timeout_ms": -100 if i % 2 == 0 else 99999999,
                    "flags": {f"dynamic_{i}": True},
                    "options": {"arbitrary": [1, 2, "bad"]},
                }
            ).encode()
        elif choice == 2:
            # Random raw bytes
            payload = bytes(rng.getrandbits(8) for _ in range(rng.randint(1, 64)))
        elif choice == 3:
            # Boundary values & strange unicode
            payload = json.dumps(
                {
                    "key": "\x00\uffff\U0001f4a9" + str(i),
                    "nested": {"deep": {"tier": -9999}},
                }
            ).encode()
        else:
            # Empty / minimal input
            payload = b"{}"

        fuzz_one_input(payload)
        passed += 1

    duration = time.perf_counter() - start
    return {
        "runs": runs,
        "passed": passed == runs,
        "duration_seconds": duration,
    }


def main() -> None:
    """Entry point for native Atheris or standalone execution."""
    if atheris is not None and len(sys.argv) > 1 and sys.argv[1] != "--standalone":
        atheris.Setup(sys.argv, fuzz_one_input)
        atheris.Fuzz()
    else:
        runs = 1000
        print(f"Running standalone feature flags fuzzer ({runs} runs)...")  # noqa: T201
        res = run_standalone(runs)
        print(  # noqa: T201
            f"Completed {res['runs']} runs in {res['duration_seconds']:.2f}s (passed: {res['passed']})"
        )


if __name__ == "__main__":
    main()
