"""Atheris coverage-guided and adversarial fuzz harness for MCP tool argument parsing.

Notes/Architectural Intent:
    Stress tests MCP tool parameter extraction, validation, and error encapsulation
    against pathological Unicode, random serialized JSON, boundary integers,
    and adversarial injection keys to verify total crash resilience.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import random
import sys
import time
from typing import Any

from pydantic import BaseModel, Field
from rodi import Container

from hexastack_cqrs.ports.buses import CommandBusPort
from hexastack_mcp.domain.exceptions import (
    ToolExecutionError,
    ToolUnauthorizedError,
    ToolValidationError,
)
from hexastack_mcp.infra.registries.server import McpServerRegistry

try:
    atheris: Any = importlib.import_module("atheris")
except ImportError:
    atheris = None


class FuzzEchoBus(CommandBusPort):
    """Stub bus returning arguments."""

    def dispatch(self, command: Any) -> Any:
        return {"dispatched": True, "type": type(command).__name__}


class FuzzTargetCommand(BaseModel):
    """Target command schema for fuzzing."""

    action: str = Field(min_length=1, max_length=100)
    limit: int = Field(default=10, ge=1, le=1000)
    active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


_container = Container()
_container.add_instance(FuzzEchoBus(), declared_class=CommandBusPort)

_registry = McpServerRegistry()
_tool_wrapper = _registry._create_cqrs_tool_wrapper(
    target_cls=FuzzTargetCommand,
    kind="command",
    container=_container,
    read_only_tool=False,
    server_read_only=False,
)

_MAX_PER_CALL_DURATION = 0.05  # 50ms


def fuzz_one_input(data: bytes) -> None:
    """Execute one fuzzed input against the MCP tool wrapper.

    Args:
        data: Arbitrary byte sequence from libFuzzer or random generator.
    """
    if not data:
        return

    # Attempt to derive structured arguments or text
    kwargs: dict[str, Any] = {}
    try:
        text = data.decode("utf-8", errors="ignore")
        if text.startswith("{") and text.endswith("}"):
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                kwargs = parsed
        else:
            kwargs = {
                "action": text[:50],
                "limit": len(data) % 2000 - 500,
                "active": (len(data) % 2 == 0),
            }
    except Exception:
        kwargs = {"raw_data": data}

    t0 = time.perf_counter()
    try:
        # Run async wrapper synchronously
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_tool_wrapper(**kwargs))
        finally:
            loop.close()
    except (ToolValidationError, ToolUnauthorizedError, ToolExecutionError):
        # Expected domain exception containment
        pass
    except Exception as exc:
        raise AssertionError(
            f"Unexpected uncontained exception during MCP tool execution: {type(exc).__name__}: {exc}"
        ) from exc

    elapsed = time.perf_counter() - t0
    if elapsed > _MAX_PER_CALL_DURATION:
        raise TimeoutError(
            f"MCP tool argument processing took {elapsed:.4f}s (> {_MAX_PER_CALL_DURATION}s)"
        )


def test_fuzz_mcp_arguments_smoke() -> None:
    """Smoke test MCP tool fuzz harness under pytest."""
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
            payload = json.dumps(
                {"action": f"test_{i}", "limit": i, "active": True}
            ).encode()
        elif choice == 1:
            # Corrupted / invalid keys
            payload = json.dumps(
                {f"invalid_key_{i}": "bad_value", "action": "ok"}
            ).encode()
        elif choice == 2:
            # Random raw bytes
            payload = bytes(rng.getrandbits(8) for _ in range(rng.randint(1, 64)))
        else:
            # Boundary values
            payload = json.dumps(
                {"action": "", "limit": -9999, "active": "not_bool"}
            ).encode()

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
        print(f"Running standalone MCP argument fuzzer ({runs} runs)...")  # noqa: T201
        res = run_standalone(runs)
        print(  # noqa: T201
            f"Completed {res['runs']} runs in {res['duration_seconds']:.2f}s (passed: {res['passed']})"
        )


if __name__ == "__main__":
    main()
