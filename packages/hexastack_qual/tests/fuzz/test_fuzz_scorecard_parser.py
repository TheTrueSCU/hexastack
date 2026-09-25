"""Atheris coverage-guided and adversarial fuzz harness for hexastack-qual report parser.

Notes/Architectural Intent:
    Stress tests QualityScorecard and MutantReport deserialization and validation
    against pathological Unicode byte streams, deeply nested payloads, boundary integers,
    and corrupted JSON to ensure zero unhandled exceptions or denial-of-service vulnerabilities.
"""

from __future__ import annotations

import importlib
import json
import random
import sys
import time
from typing import Any

from pydantic import ValidationError

try:
    atheris: Any = importlib.import_module("atheris")
except ImportError:
    atheris = None

if atheris is not None:
    with atheris.instrument_imports():
        from hexastack_qual.domain.models import (
            ComplexityMetric,
            MutantReport,
            PrHealthSummary,
            QualityScorecard,
        )
else:
    from hexastack_qual.domain.models import (
        ComplexityMetric,
        MutantReport,
        PrHealthSummary,
        QualityScorecard,
    )

_MAX_ALLOWED_DURATION_SECONDS = 0.05  # 50ms per input


def fuzz_one_input(data: bytes) -> None:
    """Execute one fuzzed input against quality model deserializers.

    Args:
        data: Arbitrary byte stream from libFuzzer or generator.

    Raises:
        TimeoutError: If validation exceeds execution threshold.
    """
    if not data:
        return

    t0 = time.perf_counter()

    # Attempt to decode as JSON or construct a structured payload
    text = data.decode("utf-8", errors="replace")
    parsed_json: Any = None
    if text.startswith("{") and text.endswith("}"):
        try:
            parsed_json = json.loads(text)
        except Exception:
            parsed_json = None

    # Test QualityScorecard parser
    try:
        if parsed_json and isinstance(parsed_json, dict):
            QualityScorecard.model_validate(parsed_json)
        else:
            QualityScorecard.model_validate_json(data)
    except (ValidationError, ValueError, UnicodeDecodeError):
        pass

    # Test MutantReport parser
    try:
        if parsed_json and isinstance(parsed_json, dict):
            MutantReport.model_validate(parsed_json)
        else:
            MutantReport.model_validate_json(data)
    except (ValidationError, ValueError, UnicodeDecodeError):
        pass

    # Test PrHealthSummary parser
    try:
        if parsed_json and isinstance(parsed_json, dict):
            PrHealthSummary.model_validate(parsed_json)
        else:
            PrHealthSummary.model_validate_json(data)
    except (ValidationError, ValueError, UnicodeDecodeError):
        pass

    # Test ComplexityMetric parser
    try:
        if parsed_json and isinstance(parsed_json, dict):
            ComplexityMetric.model_validate(parsed_json)
        else:
            ComplexityMetric.model_validate_json(data)
    except (ValidationError, ValueError, UnicodeDecodeError):
        pass

    elapsed = time.perf_counter() - t0
    if elapsed > _MAX_ALLOWED_DURATION_SECONDS:
        raise TimeoutError(
            f"Fuzz iteration exceeded maximum time limit: {elapsed:.4f}s"
        )


def test_fuzz_scorecard_parser_smoke() -> None:
    """Smoke test scorecard parser fuzz harness under pytest."""
    res = run_standalone(runs=25)
    is_passed = res["passed"]
    assert is_passed is True
    total_runs = res["runs"]
    assert total_runs == 25


def run_standalone(runs: int = 1000) -> dict[str, Any]:
    """Execute standalone fuzzing loop without requiring native libFuzzer.

    Args:
        runs: Number of random iterations to execute.

    Returns:
        Summary dict containing execution status and iteration counts.
    """
    seeds: list[bytes] = [
        b'{"target": "pkg1", "is_healthy": true}',
        b'{"package_name": "core", "total_mutants": 10, "killed_mutants": 8}',
        b'{"pr_number": 42, "title": "fix", "state": "open", "ci_status": "success"}',
        b'{"function_name": "foo", "file_path": "a.py", "line_number": 1, "complexity": 5}',
        b"",
        b"\x00" * 32,
        b"{" * 50 + b"}" * 50,
        b'{"target": "\xff\xfe\xfd"}',
        b'{"complexity": -99999999999999999999999999999999}',
    ]

    rng = random.Random(42)  # noqa: S311

    for _ in range(runs):
        choice = rng.choice(seeds)
        # Apply mutations
        mutation_type = rng.randint(0, 3)
        if mutation_type == 0:
            mutated = choice + rng.randbytes(rng.randint(1, 64))
        elif mutation_type == 1:
            mutated = rng.randbytes(rng.randint(1, 128))
        elif mutation_type == 2 and len(choice) > 2:
            idx = rng.randint(0, len(choice) - 1)
            mutated = choice[:idx] + rng.randbytes(1) + choice[idx + 1 :]
        else:
            mutated = choice

        fuzz_one_input(mutated)

    return {"passed": True, "runs": runs}


if __name__ == "__main__":
    if atheris is not None:
        atheris.Setup(sys.argv, fuzz_one_input)
        atheris.Fuzz()
    else:
        run_standalone(1000)
