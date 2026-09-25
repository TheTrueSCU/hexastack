"""Atheris coverage-guided and adversarial fuzz harness for hexastack-flow DAG execution.

Notes/Architectural Intent:
    Stress tests workflow DAG construction, topological validation, step metadata encapsulation,
    and runner execution against arbitrary dependency matrices, cycle injections,
    pathological JSON schemas, and corrupted step contexts to verify total crash resilience.
"""

from __future__ import annotations

import contextlib
import importlib
import json
import random
import sys
import time
from datetime import UTC, datetime
from typing import Any

from hexaflow.domain.exceptions import (
    DuplicateStepError,
    InvalidWorkflowDAGError,
    StepNotFoundError,
    WorkflowError,
)
from hexaflow.domain.models import StageDefinition, StepDefinition, WorkflowDefinition

from hexastack_core.domain import Command
from hexastack_cqrs.ports.buses import CommandBusPort
from hexastack_flow.adapters.cqrs.runner import CqrsWorkflowRunner
from hexastack_flow.adapters.cqrs.steps import as_command_step
from hexastack_flow.domain.models import CqrsStepMetadata, WorkflowExecutionResult

try:
    atheris: Any = importlib.import_module("atheris")
except ImportError:
    atheris = None

_MAX_PER_CALL_DURATION = 0.05  # 50ms


class FuzzEchoBus(CommandBusPort):
    """Stub bus for fuzz testing."""

    def dispatch(self, command: Command) -> Any:
        return {"dispatched": True, "type": type(command).__name__}


class FuzzCommand(Command):
    """Fuzzed command schema."""

    payload: str = "ok"


_bus = FuzzEchoBus()
_runner = CqrsWorkflowRunner()


def fuzz_one_input(data: bytes) -> None:
    """Execute one fuzzed input against flow DAG construction and metadata models.

    Args:
        data: Arbitrary byte sequence from libFuzzer or random generator.
    """
    if not data:
        return

    payload: Any = None
    try:
        text = data.decode("utf-8", errors="ignore")
        if text.startswith("{") and text.endswith("}"):
            payload = json.loads(text)
        else:
            payload = {"seed": len(data), "raw": text[:30]}
    except Exception:
        payload = {"data_len": len(data)}

    t0 = time.perf_counter()

    # 1. Fuzz CqrsStepMetadata & WorkflowExecutionResult validation
    if isinstance(payload, dict):
        with contextlib.suppress(Exception):
            _ = CqrsStepMetadata.model_validate(payload)

        # Fuzz WorkflowExecutionResult with synthesized timestamps
        with contextlib.suppress(Exception):
            synthesized = dict(payload)
            synthesized.setdefault("run_id", "run-fuzz-1")
            synthesized.setdefault("workflow_name", "wf-fuzz")
            synthesized.setdefault("status", "COMPLETED")
            synthesized.setdefault("started_at", datetime.now(UTC).isoformat())
            synthesized.setdefault("ended_at", datetime.now(UTC).isoformat())
            _ = WorkflowExecutionResult.model_validate(synthesized)

    # 2. Fuzz step adapter construction
    step_name = f"step_{len(data) % 10}"
    cmd_step_def = as_command_step(
        name=step_name,
        command_factory=lambda ctx: FuzzCommand(payload=f"val_{len(data)}"),
        command_bus=_bus,
        description="Fuzzed command step",
        timeout_seconds=0.1,
    )
    is_step_def = isinstance(cmd_step_def, StepDefinition)
    assert is_step_def is True

    # 3. Fuzz DAG construction with arbitrary dependency topology
    num_steps = max(2, (len(data) % 5) + 2)
    step_names = [f"s_{i}" for i in range(num_steps)]
    steps: list[StepDefinition] = []

    for i, sname in enumerate(step_names):
        # Create dependencies using fuzzed bytes
        dep_indices: list[int] = []
        if i > 0 and len(data) > i:
            byte_val = data[i % len(data)]
            if byte_val % 3 == 0:
                dep_indices.append((i - 1) % num_steps)
            elif byte_val % 3 == 1 and i > 1:
                dep_indices.append((i - 2) % num_steps)
            elif byte_val % 7 == 0:
                # Deliberate cycle injection
                dep_indices.append((i + 1) % num_steps)

        deps = tuple(step_names[idx] for idx in dep_indices)
        step = StepDefinition(
            name=sname,
            action=lambda ctx: {"ok": True},
            depends_on=deps,
        )
        steps.append(step)

    stage = StageDefinition(name="stage_fuzz", steps=tuple(steps))

    try:
        wf = WorkflowDefinition(
            name=f"wf_{len(data)}",
            stages=(stage,),
        )
        # If construction succeeded, DAG is acyclic and valid
        result = _runner.execute(wf)
        status_ok = isinstance(result.status, str)
        assert status_ok is True
    except (
        InvalidWorkflowDAGError,
        StepNotFoundError,
        DuplicateStepError,
        WorkflowError,
    ):
        # Expected domain exception containment for invalid or cyclic topologies
        pass
    except AssertionError:
        raise
    except Exception as exc:
        raise AssertionError(
            f"Unexpected uncontained exception during DAG validation/execution: {type(exc).__name__}: {exc}"
        ) from exc

    elapsed = time.perf_counter() - t0
    if elapsed > _MAX_PER_CALL_DURATION:
        raise TimeoutError(
            f"Flow DAG fuzz execution took {elapsed:.4f}s (> {_MAX_PER_CALL_DURATION}s)"
        )


def test_fuzz_flow_dag_smoke() -> None:
    """Smoke test workflow DAG fuzz harness under pytest."""
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

    for i in range(runs):
        choice = i % 5
        if choice == 0:
            # Linear DAG
            payload = bytes([i, i + 1, 0, 1])
        elif choice == 1:
            # JSON payload testing metadata validation
            payload = json.dumps(
                {
                    "step_type": "command" if i % 2 == 0 else "query",
                    "message_type": f"app.domain.Command{i}",
                    "requires_transaction": (i % 2 == 0),
                    "description": f"Metadata test {i}",
                }
            ).encode()
        elif choice == 2:
            # Random raw bytes
            payload = bytes(rng.getrandbits(8) for _ in range(rng.randint(2, 32)))
        elif choice == 3:
            # Cycle injection bytes
            payload = bytes([0, 14, 21, 28, 35])
        else:
            # Minimal / edge bytes
            payload = b"\x00\x01\x02"

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
        print(f"Running standalone flow DAG fuzzer ({runs} runs)...")  # noqa: T201
        res = run_standalone(runs)
        print(  # noqa: T201
            f"Completed {res['runs']} runs in {res['duration_seconds']:.2f}s (passed: {res['passed']})"
        )


if __name__ == "__main__":
    main()
