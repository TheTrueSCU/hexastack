"""Atheris coverage-guided fuzzing harness for ProtoCompiler in hexastack-grpc.

Notes/Architectural Intent:
    Stress tests in-process protoc schema parsing and AST tokenization against
    malformed syntax, deeply nested messages, invalid directives, and pathological
    byte streams to guarantee memory safety, clean exception handling, and zero segfaults.
"""

from __future__ import annotations

import contextlib
import os
import sys
import tempfile
import time
from typing import Any

try:
    import atheris

    with atheris.instrument_imports():
        from hexastack_grpc.domain.exceptions import ProtoCompilationError
        from hexastack_grpc.domain.models import ProtoSchemaMetadata
        from hexastack_grpc.infra.compiler import ProtoCompiler
except ImportError:
    atheris = None  # type: ignore[assignment]
    from hexastack_grpc.domain.exceptions import ProtoCompilationError
    from hexastack_grpc.domain.models import ProtoSchemaMetadata
    from hexastack_grpc.infra.compiler import ProtoCompiler


_PROTO_TEMPLATES = [
    'syntax = "proto3";\npackage fuzz;\nmessage Root {\n  string name = 1;\n}\n',
    'syntax = "proto3";\nmessage Node {\n  int32 id = 1;\n  repeated Node children = 2;\n}\n',
    'syntax = "proto2";\nmessage Legacy {\n  required string val = 1;\n}\n',
]


def _build_mutated_schema(data: bytes) -> str:
    """Construct an adversarial or mutated proto schema from fuzzed data."""
    if atheris is not None and hasattr(atheris, "FuzzedDataProvider"):
        fdp = atheris.FuzzedDataProvider(data)
        choice = fdp.ConsumeIntInRange(0, 3)
        if choice == 0:
            # Completely arbitrary text
            return fdp.ConsumeUnicodeNoSurrogates(min(len(data), 2048))
        if choice == 1:
            # Template with injected mutated field names / numbers
            prefix = _PROTO_TEMPLATES[
                fdp.ConsumeIntInRange(0, len(_PROTO_TEMPLATES) - 1)
            ]
            injection = fdp.ConsumeUnicodeNoSurrogates(128)
            return (
                f"{prefix}\n// {injection}\nmessage Mutated {{\n  string f = 100;\n}}"
            )
        # Deeply nested message schema
        depth = fdp.ConsumeIntInRange(1, 40)
        schema = 'syntax = "proto3";\n'
        for i in range(depth):
            schema += f"message M{i} {{\n"
        schema += "  string leaf = 1;\n" + ("}\n" * depth)
        return schema
    # Standalone fallback
    return data.decode("utf-8", errors="replace")[:2048]


@contextlib.contextmanager
def _suppress_c_stderr():
    """Redirect OS-level stderr (fd 2) to /dev/null to silence C++ protoc parser warnings."""
    sys.stderr.flush()
    old_stderr = os.dup(2)
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        sys.stderr.flush()
        os.dup2(old_stderr, 2)
        os.close(old_stderr)


def test_one_input(data: bytes) -> None:
    """Test one fuzzed input against ProtoCompiler.compile_metadata.

    Args:
        data: Arbitrary fuzzed bytes from fuzzer.

    Raises:
        AssertionError: If compilation raises an unhandled, unexpected exception.
    """
    if not data:
        return

    schema_str = _build_mutated_schema(data)
    meta = ProtoSchemaMetadata(
        target=object, message_name="FuzzMessage", schema=schema_str
    )

    with tempfile.TemporaryDirectory() as tmp_out:
        try:
            with _suppress_c_stderr():
                outputs = ProtoCompiler.compile_metadata([meta], output_dir=tmp_out)
            # If it succeeded, outputs should contain generated files
            assert isinstance(outputs, list)
        except ProtoCompilationError:
            # Expected graceful failure when schema has syntax errors
            pass
        except Exception as exc:
            # Uncaught exceptions (e.g. segfault, unhandled OS error) constitute a bug
            raise AssertionError(
                f"Unhandled exception during proto compilation: {exc}"
            ) from exc


def run_standalone(runs: int = 500) -> dict[str, Any]:
    """Execute standalone fuzzing loop for ProtoCompiler without native libFuzzer.

    Args:
        runs: Number of iterations.

    Returns:
        Execution summary dictionary.
    """
    start_time = time.perf_counter()
    crashes = 0

    for i in range(runs):
        seed = os.urandom(min(32 + (i % 256), 2048))
        try:
            test_one_input(seed)
        except Exception:
            crashes += 1

    total_time = time.perf_counter() - start_time
    return {
        "target": "ProtoCompiler",
        "engine": "standalone",
        "runs": runs,
        "duration_seconds": round(total_time, 3),
        "crashes": crashes,
        "passed": crashes == 0,
    }


def run_atheris(runs: int = 500) -> dict[str, Any]:
    """Execute Atheris coverage-guided fuzzing for ProtoCompiler.

    Args:
        runs: Number of libFuzzer iterations.

    Returns:
        Execution summary dictionary.
    """
    if atheris is None:
        return run_standalone(runs=runs)

    start_time = time.perf_counter()
    crashes = 0

    def harness(data: bytes) -> None:
        nonlocal crashes
        try:
            test_one_input(data)
        except AssertionError:
            crashes += 1

    args = sys.argv[:1] + [f"-runs={runs}", "-max_len=2048"]
    try:
        atheris.Setup(args, harness)
        atheris.Fuzz()
    except Exception:
        crashes += 1

    total_time = time.perf_counter() - start_time
    return {
        "target": "ProtoCompiler",
        "engine": "atheris",
        "runs": runs,
        "duration_seconds": round(total_time, 3),
        "crashes": crashes,
        "passed": crashes == 0,
    }


def main() -> None:
    """CLI entrypoint for standalone Atheris execution."""
    if atheris is not None and len(sys.argv) > 1:
        atheris.Setup(sys.argv, test_one_input)
        atheris.Fuzz()
    else:
        res = run_standalone(runs=500)
        print(f"ProtoCompiler fuzzing completed: {res}")


__all__ = [
    "main",
    "run_atheris",
    "run_standalone",
    "test_one_input",
]

if __name__ == "__main__":
    main()
