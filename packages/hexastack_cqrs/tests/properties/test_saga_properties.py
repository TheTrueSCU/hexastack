"""Hypothesis property-based tests for Saga orchestration and compensation invariants.

Notes/Architectural Intent:
    Fuzzes arbitrary Saga execution flows to prove mathematical invariants:
    1. Forward Execution Order: Steps 0..N-1 execute in sequential FIFO order on happy path.
    2. LIFO Compensation: When a failure is injected at step k, exactly steps k-1..0
       are compensated in strict reverse order; steps > k are never invoked.
    3. Failure Escalation: When compensation fails, SagaCompensationError is raised
       and state transitions to FAILED.
    4. Async/Sync Isomorphism: execute and execute_async preserve identical state transitions.
"""

from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hexastack_cqrs.adapters.sagas import (
    InMemorySagaOrchestrator,
    InMemorySagaStorage,
)
from hexastack_cqrs.domain.sagas import (
    SagaCompensationError,
    SagaDefinition,
    SagaStatus,
    SagaStep,
)
from hexastack_cqrs.infra.sagas import SagaBuilder

clean_names = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    min_size=3,
    max_size=15,
)


@given(
    step_count=st.integers(min_value=1, max_value=8),
)
@settings(max_examples=50)
def test_saga_happy_path_fifo_order_property(step_count: int) -> None:
    """Property: All steps execute in strict sequential FIFO order when no failure occurs."""
    execution_trace: list[str] = []
    compensation_trace: list[str] = []

    steps: list[SagaStep] = []
    for i in range(step_count):
        step_name = f"step_{i}"

        def make_action(name: str):
            return lambda ctx: (execution_trace.append(name), f"res_{name}")[1]

        def make_compensation(name: str):
            return lambda res, ctx: compensation_trace.append(name)

        steps.append(
            SagaStep(
                name=step_name,
                action=make_action(step_name),
                compensation=make_compensation(step_name),
            )
        )

    definition = SagaDefinition(name="happy_path_saga", steps=steps)
    storage = InMemorySagaStorage()
    orchestrator = InMemorySagaOrchestrator(storage=storage)

    result = orchestrator.execute(definition)

    # Invariant 1: Status is COMPLETED and not compensated
    assert result.status == SagaStatus.COMPLETED
    assert result.compensated is False
    assert result.error is None

    # Invariant 2: Forward execution happened in exact FIFO order
    expected_forward = [f"step_{i}" for i in range(step_count)]
    assert execution_trace == expected_forward

    # Invariant 3: No compensation was ever called
    assert compensation_trace == []

    # Invariant 4: Storage matches completed result
    state = storage.get_state(result.saga_id)
    assert state is not None
    assert state.status == SagaStatus.COMPLETED
    assert len(state.step_results) == step_count


@given(
    step_count=st.integers(min_value=1, max_value=8),
    fail_index=st.integers(min_value=0, max_value=7),
)
@settings(max_examples=50)
def test_saga_failure_strict_lifo_compensation_property(
    step_count: int, fail_index: int
) -> None:
    """Property: When step k fails, exactly steps k-1..0 compensate in strict LIFO order."""
    effective_fail = fail_index % step_count
    execution_trace: list[str] = []
    compensation_trace: list[str] = []

    steps: list[SagaStep] = []
    for i in range(step_count):
        step_name = f"step_{i}"
        should_fail = i == effective_fail

        def make_action(name: str, fails: bool):
            def _action(ctx: Any) -> str:
                execution_trace.append(name)
                if fails:
                    raise RuntimeError(f"fault_{name}")
                return f"res_{name}"

            return _action

        def make_compensation(name: str):
            return lambda res, ctx=None: compensation_trace.append(name)

        steps.append(
            SagaStep(
                name=step_name,
                action=make_action(step_name, should_fail),
                compensation=make_compensation(step_name),
            )
        )

    definition = SagaDefinition(name="compensation_saga", steps=steps)
    storage = InMemorySagaStorage()
    orchestrator = InMemorySagaOrchestrator(storage=storage)

    result = orchestrator.execute(definition)

    # Invariant 1: Status is COMPENSATED
    assert result.status == SagaStatus.COMPENSATED
    assert result.compensated is True
    assert result.error == f"fault_step_{effective_fail}"

    # Invariant 2: Steps executed up to and including the failing step, none beyond
    expected_forward = [f"step_{i}" for i in range(effective_fail + 1)]
    assert execution_trace == expected_forward

    # Invariant 3: Strict LIFO compensation for all completed steps (effective_fail-1 down to 0)
    expected_compensation = [f"step_{i}" for i in reversed(range(effective_fail))]
    assert compensation_trace == expected_compensation

    # Invariant 4: Storage recorded compensated steps and status
    state = storage.get_state(result.saga_id)
    assert state is not None
    assert state.status == SagaStatus.COMPENSATED
    assert state.compensated_steps == expected_compensation


@given(
    step_count=st.integers(min_value=2, max_value=6),
    fail_index=st.integers(min_value=1, max_value=5),
)
@settings(max_examples=40)
def test_saga_compensation_failure_escalation_property(
    step_count: int, fail_index: int
) -> None:
    """Property: When a compensation action fails, SagaCompensationError is raised and status is FAILED."""
    effective_fail = max(1, fail_index % step_count)
    # Target compensation failure at the immediate predecessor
    comp_fail_index = effective_fail - 1

    steps: list[SagaStep] = []
    for i in range(step_count):
        step_name = f"step_{i}"
        forward_fails = i == effective_fail
        comp_fails = i == comp_fail_index

        def make_action(name: str, fails: bool):
            def _action(ctx: Any) -> str:
                if fails:
                    raise RuntimeError(f"forward_fault_{name}")
                return f"res_{name}"

            return _action

        def make_compensation(name: str, fails: bool):
            def _comp(res: Any, ctx: Any = None) -> None:
                if fails:
                    raise RuntimeError(f"comp_fault_{name}")

            return _comp

        steps.append(
            SagaStep(
                name=step_name,
                action=make_action(step_name, forward_fails),
                compensation=make_compensation(step_name, comp_fails),
            )
        )

    definition = SagaDefinition(name="comp_failure_saga", steps=steps)
    storage = InMemorySagaStorage()
    orchestrator = InMemorySagaOrchestrator(storage=storage)

    with pytest.raises(SagaCompensationError) as exc_info:
        orchestrator.execute(definition)

    assert f"step_{comp_fail_index}" in str(exc_info.value)

    # Invariant: Stored status must be FAILED
    states = list(storage._states.values())
    assert len(states) == 1
    assert states[0].status == SagaStatus.FAILED


@pytest.mark.asyncio
@given(
    step_count=st.integers(min_value=1, max_value=6),
    fail_index=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=30)
async def test_saga_async_isomorphism_property(
    step_count: int, fail_index: int
) -> None:
    """Property: execute_async produces identical LIFO compensation behavior for async steps."""
    effective_fail = fail_index % step_count
    execution_trace: list[str] = []
    compensation_trace: list[str] = []

    builder = SagaBuilder(name="async_isomorphic_saga")
    for i in range(step_count):
        step_name = f"step_{i}"
        should_fail = i == effective_fail

        def make_async_action(name: str, fails: bool):
            async def _action(ctx: Any) -> str:
                execution_trace.append(name)
                if fails:
                    raise RuntimeError(f"async_fault_{name}")
                return f"res_{name}"

            return _action

        def make_async_compensation(name: str):
            async def _comp(res: Any, ctx: Any = None) -> None:
                compensation_trace.append(name)

            return _comp

        builder.step(
            name=step_name,
            action=make_async_action(step_name, should_fail),
            compensate=make_async_compensation(step_name),
        )

    definition = builder.build()
    storage = InMemorySagaStorage()
    orchestrator = InMemorySagaOrchestrator(storage=storage)

    result = await orchestrator.execute_async(definition)

    assert result.status == SagaStatus.COMPENSATED
    assert result.compensated is True
    expected_forward = [f"step_{i}" for i in range(effective_fail + 1)]
    assert execution_trace == expected_forward
    expected_comp = [f"step_{i}" for i in reversed(range(effective_fail))]
    assert compensation_trace == expected_comp
