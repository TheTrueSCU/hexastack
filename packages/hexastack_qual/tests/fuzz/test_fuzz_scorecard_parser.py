"""Atheris coverage-guided and adversarial fuzz harness for quality scorecard parsing.

Notes/Architectural Intent:
    Stress tests QualityScorecard, MutantReport, and ComplexityMetric JSON deserializers
    against pathological Unicode, mutated JSON structures, recursive dictionaries,
    and truncated byte payloads to verify schema validation resilience and zero crash defects.
"""

from __future__ import annotations

import importlib
import json
import random
import sys
import time
from typing import Any

from hexastack_qual.domain.models import (
    ComplexityMetric,
    MutantReport,
    QualityScorecard,
)
from pydantic import ValidationError

try:
    atheris: Any = importlib.import_module("atheris")
except ImportError:
    atheris = None

_MAX_ALLOWED_DURATION_SECONDS = 0.05  # 50ms per input


def fuzz_one_input(data: bytes) -> None:
    """Execute one fuzzed input against quality model deserializers.

    Args:
        data: Arbitrary byte stream from libFuzzer or random generator.
    """
    if not data:
        return

    # Decode with fallback
    text = data.decode("utf-8", errors="replace")

    t0 = time.perf_counter()

    # Fuzz QualityScorecard JSON parsing
    try:
        QualityScorecard.model_validate_json(text)
    except (ValidationError, ValueError):
        pass
    except Exception as exc:
        raise AssertionError(
            f"QualityScorecard parsing crashed with unexpected exception: {type(exc).__name__}: {exc}"
        ) from exc

    # Fuzz MutantReport JSON parsing
    try:
        MutantReport.model_validate_json(text)
    except (ValidationError, ValueError):
        pass
    except Exception as exc:
        raise AssertionError(
            f"MutantReport parsing crashed with unexpected exception: {type(exc).__name__}: {exc}"
        ) from exc

    # Fuzz ComplexityMetric JSON parsing
    try:
        ComplexityMetric.model_validate_json(text)
    except (ValidationError, ValueError):
        pass
    except Exception as exc:
        raise AssertionError(
            f"ComplexityMetric parsing crashed with unexpected exception: {type(exc).__name__}: {exc}"
        ) from exc

    elapsed = time.perf_counter() - t0
    if elapsed > _MAX_ALLOWED_DURATION_SECONDS:
        raise TimeoutError(
            f"Quality scorecard parsing took {elapsed:.4f}s (> {_MAX_ALLOWED_DURATION_SECONDS}s)"
        )


def test_fuzz_scorecard_parser_smoke() -> None:
    """Smoke test quality scorecard parser fuzz harness under pytest."""
    res = run_standalone(runs=25)
    assert res["passed"] is True


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

    for i in range(runs):
        choice = i % 4
        if choice == 0:
            # Valid minimal scorecard
            payload = json.dumps(
                {"target": f"pkg_{i}", "is_healthy": (i % 2 == 0), "checks": []}
            ).encode()
        elif choice == 1:
            # Corrupted / invalid types
            payload = json.dumps(
                {"target": 12345, "is_healthy": "invalid_bool", "checks": "not_a_list"}
            ).encode()
        elif choice == 2:
            # Random raw bytes
            payload = bytes(rng.getrandbits(8) for _ in range(rng.randint(1, 128)))
        else:
            # Truncated or malformed JSON
            payload = (
                b'{"target": "pkg", "is_healthy": true, "checks": [{"check_name": '
            )

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
        print(f"Running standalone scorecard parser fuzzer ({runs} runs)...")  # noqa: T201
        res = run_standalone(runs)
        print(  # noqa: T201
            f"Completed {res['runs']} runs in {res['duration_seconds']:.2f}s (passed: {res['passed']})"
        )


if __name__ == "__main__":
    main()
