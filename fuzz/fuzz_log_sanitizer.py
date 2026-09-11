"""Atheris coverage-guided fuzzing harness for LogSanitizer.

Notes/Architectural Intent:
    Stress tests LogSanitizer regex pattern matching and nested dictionary traversal
    against pathological Unicode byte streams, mutated credit card / bearer sequences,
    and adversarial nested payloads to verify polynomial ReDoS immunity and zero crash defects.
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

try:
    import atheris

    with atheris.instrument_imports():
        from hexastack_logging.infra.sanitizer import LogSanitizer
except ImportError:
    atheris = None  # type: ignore[assignment]
    from hexastack_logging.infra.sanitizer import LogSanitizer


_MAX_ALLOWED_DURATION_SECONDS = 0.05  # 50ms ReDoS threshold per input
_sanitizer = LogSanitizer()


def test_one_input(data: bytes) -> None:
    """Test one input against LogSanitizer regex and structural traversal.

    Args:
        data: Arbitrary fuzzed byte sequence from libFuzzer or generator.

    Raises:
        TimeoutError: If pattern matching exceeds the ReDoS threshold.
        AssertionError: If an invariant is violated.
    """
    if not data:
        return

    if atheris is not None and hasattr(atheris, "FuzzedDataProvider"):
        fdp = atheris.FuzzedDataProvider(data)
        str_len = fdp.ConsumeIntInRange(0, min(len(data), 2048))
        text = fdp.ConsumeUnicodeNoSurrogates(str_len)
        dict_key = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 32))
        dict_val = fdp.ConsumeUnicodeNoSurrogates(fdp.ConsumeIntInRange(0, 128))
    else:
        # Standalone byte decoding fallback
        text = data.decode("utf-8", errors="replace")[:2048]
        dict_key = "key_" + str(len(data))
        dict_val = text[:64]

    # Invariant 1: sanitize_string finishes well within ReDoS threshold
    t0 = time.perf_counter()
    scrubbed = _sanitizer.sanitize_string(text)
    elapsed = time.perf_counter() - t0

    if elapsed > _MAX_ALLOWED_DURATION_SECONDS:
        raise TimeoutError(
            f"Potential ReDoS detected: LogSanitizer took {elapsed:.4f}s (> {_MAX_ALLOWED_DURATION_SECONDS}s) on input {text!r}"
        )

    assert isinstance(scrubbed, str)

    # Invariant 2: sanitize_dict preserves non-sensitive structures and redacts keys
    payload: dict[str, Any] = {
        dict_key: dict_val,
        "password": "supersecretpassword123",  # pragma: allowlist secret
        "nested": {
            "token": "token_abc_xyz",
            "safe_field": text,
        },  # pragma: allowlist secret
        "items": [text, "Bearer eyJhbGciOiJIUzI1NiJ9.secret.token"],
    }
    sanitized = _sanitizer.sanitize_dict(payload)
    assert isinstance(sanitized, dict)
    assert sanitized["password"] == "***REDACTED***"
    assert sanitized["nested"]["token"] == "***REDACTED***"
    assert "eyJhbGciOiJIUzI1NiJ9.secret.token" not in sanitized["items"][1]

    # Invariant 3: sanitize_traceback runs safely
    tb_out = _sanitizer.sanitize_traceback(f"Traceback: in module error: {text}")
    assert isinstance(tb_out, str)


def run_standalone(runs: int = 1000) -> dict[str, Any]:
    """Execute standalone fuzzing loop without requiring native libFuzzer.

    Args:
        runs: Number of fuzzed iterations to execute.

    Returns:
        Dictionary summarizing runs, duration, and error count.
    """
    start_time = time.perf_counter()
    crashes = 0
    redos_violations = 0

    for i in range(runs):
        # Generate pseudo-random mutated byte sequence with pathological edge cases
        seed_bytes = os.urandom(min(64 + (i % 512), 4096))
        # Inject adversarial candidates periodically
        if i % 5 == 0:
            seed_bytes = b"Bearer " + b"A" * (i % 256) + b" " + seed_bytes
        elif i % 7 == 0:
            seed_bytes = b"4111" + b" " * (i % 10) + b"2222 3333 4444" + seed_bytes

        try:
            test_one_input(seed_bytes)
        except TimeoutError:
            redos_violations += 1
        except Exception:
            crashes += 1

    total_time = time.perf_counter() - start_time
    return {
        "target": "LogSanitizer",
        "engine": "standalone",
        "runs": runs,
        "duration_seconds": round(total_time, 3),
        "crashes": crashes,
        "redos_violations": redos_violations,
        "passed": crashes == 0 and redos_violations == 0,
    }


def run_atheris(runs: int = 1000) -> dict[str, Any]:
    """Execute Atheris coverage-guided fuzzing with libFuzzer.

    Args:
        runs: Maximum number of runs to execute.

    Returns:
        Dictionary summarizing execution outcome.
    """
    if atheris is None:
        return run_standalone(runs=runs)

    start_time = time.perf_counter()
    crashes = 0
    redos_violations = 0

    def harness(data: bytes) -> None:
        nonlocal crashes, redos_violations
        try:
            test_one_input(data)
        except TimeoutError:
            redos_violations += 1
        except AssertionError:
            crashes += 1

    args = sys.argv[:1] + [f"-runs={runs}", "-max_len=4096"]
    try:
        atheris.Setup(args, harness)
        atheris.Fuzz()
    except Exception:
        crashes += 1

    total_time = time.perf_counter() - start_time
    return {
        "target": "LogSanitizer",
        "engine": "atheris",
        "runs": runs,
        "duration_seconds": round(total_time, 3),
        "crashes": crashes,
        "redos_violations": redos_violations,
        "passed": crashes == 0 and redos_violations == 0,
    }


def main() -> None:
    """CLI entrypoint for standalone Atheris execution."""
    if atheris is not None and len(sys.argv) > 1:
        atheris.Setup(sys.argv, test_one_input)
        atheris.Fuzz()
    else:
        res = run_standalone(runs=1000)
        print(f"Fuzzing completed: {res}")


__all__ = [
    "main",
    "run_atheris",
    "run_standalone",
    "test_one_input",
]

if __name__ == "__main__":
    main()
