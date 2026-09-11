"""Unit tests for InMemorySagaOrchestrator and InMemorySagaStorage.

Notes/Architectural Intent:
    Verifies that InMemorySagaOrchestrator executes forward steps sequentially, captures state,
    and automatically unwinds compensating actions in strict reverse (LIFO) order upon failure.
"""

import pytest

from hexastack_core.domain.command import Command
from hexastack_cqrs.adapters.buses.command.synchronous import SynchronousCommandBus
from hexastack_cqrs.adapters.sagas.in_memory import (
    InMemorySagaOrchestrator,
    InMemorySagaStorage,
)
from hexastack_cqrs.domain.sagas import (
    SagaCompensationError,
    SagaDefinition,
    SagaState,
    SagaStatus,
    SagaStep,
)
from hexastack_cqrs.infra.registries import HandlerRegistry


class CreateOrderCmd(Command):
    order_id: str


class CancelOrderCmd(Command):
    order_id: str


def test_in_memory_saga_storage():
    """Verify storage save, retrieval, and clear operations."""
    storage = InMemorySagaStorage()
    state = SagaState(saga_id="saga-1", saga_name="SampleSaga")

    storage.save_state(state)
    retrieved = storage.get_state("saga-1")
    assert retrieved is not None
    assert retrieved.saga_name == "SampleSaga"

    storage.clear()
    cleared = storage.get_state("saga-1")
    assert cleared is None


def test_in_memory_saga_orchestrator_success():
    """Verify happy path where all steps execute forward successfully."""
    trace: list[str] = []

    def step1():
        trace.append("step1")
        return {"step1": "done"}

    def step2(ctx):
        trace.append("step2")
        return {"step2": "done", "prev": ctx["Step1"]}

    definition = SagaDefinition(
        name="HappyPathSaga",
        steps=(
            SagaStep(
                name="Step1", action=step1, compensation=lambda: trace.append("comp1")
            ),
            SagaStep(
                name="Step2", action=step2, compensation=lambda: trace.append("comp2")
            ),
        ),
    )

    orchestrator = InMemorySagaOrchestrator()
    result = orchestrator.execute(definition)

    assert result.status == SagaStatus.COMPLETED
    assert result.compensated is False
    assert result.error is None
    assert trace == ["step1", "step2"]
    assert result.step_results["Step1"] == {"step1": "done"}
    assert result.step_results["Step2"]["prev"] == {"step1": "done"}


def test_in_memory_saga_orchestrator_failure_and_lifo_compensation():
    """Verify that failure on Step 3 unwinds Step 2 and Step 1 compensations in LIFO order."""
    trace: list[str] = []

    def act1():
        trace.append("act1")
        return "res1"

    def comp1(res):
        trace.append(f"comp1_{res}")

    def act2():
        trace.append("act2")
        return "res2"

    def comp2(res):
        trace.append(f"comp2_{res}")

    def act3():
        trace.append("act3")
        raise ValueError("Service unavailable at step 3")

    definition = SagaDefinition(
        name="TripFailureSaga",
        steps=(
            SagaStep(name="Step1", action=act1, compensation=comp1),
            SagaStep(name="Step2", action=act2, compensation=comp2),
            SagaStep(
                name="Step3", action=act3, compensation=lambda: trace.append("comp3")
            ),
        ),
    )

    storage = InMemorySagaStorage()
    orchestrator = InMemorySagaOrchestrator(storage=storage)
    result = orchestrator.execute(definition)

    assert result.status == SagaStatus.COMPENSATED
    assert result.compensated is True
    assert "Service unavailable at step 3" in (result.error or "")

    # Invariant: Step 3 failed, so only Step 2 then Step 1 are compensated in LIFO order!
    assert trace == [
        "act1",
        "act2",
        "act3",
        "comp2_res2",
        "comp1_res1",
    ]

    stored_state = storage.get_state(result.saga_id)
    assert stored_state is not None
    assert stored_state.status == SagaStatus.COMPENSATED
    assert stored_state.compensated_steps == ["Step2", "Step1"]


def test_in_memory_saga_orchestrator_compensation_failure_raises_error():
    """Verify that a failing compensation marks status as FAILED and raises SagaCompensationError."""
    trace: list[str] = []

    def act1():
        trace.append("act1")
        return "res1"

    def comp1():
        trace.append("comp1_fail")
        raise RuntimeError("Compensation network partition")

    def act2():
        trace.append("act2")
        raise ValueError("Step 2 failed")

    definition = SagaDefinition(
        name="BrokenCompensationSaga",
        steps=(
            SagaStep(name="Step1", action=act1, compensation=comp1),
            SagaStep(name="Step2", action=act2, compensation=None),
        ),
    )

    storage = InMemorySagaStorage()
    orchestrator = InMemorySagaOrchestrator(storage=storage)

    with pytest.raises(SagaCompensationError, match="Compensation network partition"):
        orchestrator.execute(definition)

    # Check state was recorded as FAILED
    all_states = list(storage._states.values())
    assert len(all_states) == 1
    assert all_states[0].status == SagaStatus.FAILED


def test_in_memory_saga_orchestrator_command_bus_integration():
    """Verify forward and compensation dispatch through CommandBusPort."""
    bus_trace: list[str] = []

    handler_reg = HandlerRegistry()
    handler_reg.register(
        CreateOrderCmd,
        lambda cmd: (bus_trace.append(f"create_{cmd.order_id}"), "order_created")[1],
    )
    handler_reg.register(
        CancelOrderCmd,
        lambda cmd: (bus_trace.append(f"cancel_{cmd.order_id}"), "order_cancelled")[1],
    )

    bus = SynchronousCommandBus(handler_registry=handler_reg)
    orchestrator = InMemorySagaOrchestrator(command_bus=bus)

    def failing_step():
        raise RuntimeError("Payment rejected")

    definition = SagaDefinition(
        name="BusOrderSaga",
        steps=(
            SagaStep(
                name="OrderStep",
                action=CreateOrderCmd(order_id="ord-99"),
                compensation=CancelOrderCmd(order_id="ord-99"),
            ),
            SagaStep(name="PayStep", action=failing_step, compensation=None),
        ),
    )

    result = orchestrator.execute(definition)

    assert result.status == SagaStatus.COMPENSATED
    assert bus_trace == ["create_ord-99", "cancel_ord-99"]


def test_in_memory_saga_orchestrator_command_without_bus_returns_compensated_error():
    """Verify that using Command instances without a configured CommandBusPort returns COMPENSATED with error."""
    orchestrator = InMemorySagaOrchestrator(command_bus=None)
    definition = SagaDefinition(
        name="NoBusSaga",
        steps=(SagaStep(name="Step1", action=CreateOrderCmd(order_id="x")),),
    )

    result = orchestrator.execute(definition)
    assert result.status == SagaStatus.COMPENSATED
    assert result.compensated is True
    assert "no CommandBusPort provided" in (result.error or "")


@pytest.mark.anyio
async def test_in_memory_saga_orchestrator_async():
    """Verify asynchronous forward execution and compensation unwinding."""
    async_trace: list[str] = []

    async def async_act1():
        async_trace.append("async_act1")
        return "async_res1"

    async def async_comp1(res):
        async_trace.append(f"async_comp1_{res}")

    async def async_act2():
        async_trace.append("async_act2")
        raise ValueError("Async step 2 exploded")

    definition = SagaDefinition(
        name="AsyncSaga",
        steps=(
            SagaStep(name="Step1", action=async_act1, compensation=async_comp1),
            SagaStep(name="Step2", action=async_act2, compensation=None),
        ),
    )

    orchestrator = InMemorySagaOrchestrator()
    result = await orchestrator.execute_async(definition)

    assert result.status == SagaStatus.COMPENSATED
    assert result.compensated is True
    assert async_trace == [
        "async_act1",
        "async_act2",
        "async_comp1_async_res1",
    ]


@pytest.mark.anyio
async def test_in_memory_saga_orchestrator_async_success():
    """Verify asynchronous forward execution on happy path."""
    async_trace: list[str] = []

    async def act1():
        async_trace.append("act1")
        return {"step1": "val1"}

    async def act2(ctx):
        async_trace.append("act2")
        return {"step2": "val2", "prev": ctx["Step1"]}

    definition = SagaDefinition(
        name="AsyncHappySaga",
        steps=(
            SagaStep(name="Step1", action=act1, compensation=None),
            SagaStep(name="Step2", action=act2, compensation=None),
        ),
    )

    orchestrator = InMemorySagaOrchestrator()
    result = await orchestrator.execute_async(definition)

    assert result.status == SagaStatus.COMPLETED
    assert result.compensated is False
    assert result.error is None
    assert async_trace == ["act1", "act2"]
    assert result.step_results["Step1"] == {"step1": "val1"}
    assert result.step_results["Step2"]["prev"] == {"step1": "val1"}


@pytest.mark.anyio
async def test_in_memory_saga_orchestrator_async_compensation_failure():
    """Verify async compensation failure raises SagaCompensationError and sets state to FAILED."""

    async def act1():
        return "val1"

    async def comp1(res, ctx):
        raise RuntimeError("Async compensation failed fatally")

    async def act2():
        raise ValueError("Forward step 2 failed")

    definition = SagaDefinition(
        name="AsyncBrokenCompSaga",
        steps=(
            SagaStep(name="Step1", action=act1, compensation=comp1),
            SagaStep(name="Step2", action=act2, compensation=None),
        ),
    )

    storage = InMemorySagaStorage()
    orchestrator = InMemorySagaOrchestrator(storage=storage)

    with pytest.raises(
        SagaCompensationError, match="Async compensation failed fatally"
    ):
        await orchestrator.execute_async(definition)

    states = list(storage._states.values())
    assert len(states) == 1
    assert states[0].status == SagaStatus.FAILED


@pytest.mark.anyio
async def test_in_memory_saga_orchestrator_async_command_bus_integration():
    """Verify async execution with Command objects dispatched through CommandBus."""
    bus_trace: list[str] = []

    handler_reg = HandlerRegistry()
    handler_reg.register(
        CreateOrderCmd,
        lambda cmd: (bus_trace.append(f"create_{cmd.order_id}"), "order_created")[1],
    )
    handler_reg.register(
        CancelOrderCmd,
        lambda cmd: (bus_trace.append(f"cancel_{cmd.order_id}"), "order_cancelled")[1],
    )

    bus = SynchronousCommandBus(handler_registry=handler_reg)
    orchestrator = InMemorySagaOrchestrator(command_bus=bus)

    async def failing_step():
        raise RuntimeError("Stock depleted")

    definition = SagaDefinition(
        name="AsyncBusSaga",
        steps=(
            SagaStep(
                name="OrderStep",
                action=CreateOrderCmd(order_id="ord-async-1"),
                compensation=CancelOrderCmd(order_id="ord-async-1"),
            ),
            SagaStep(name="StockStep", action=failing_step, compensation=None),
        ),
    )

    result = await orchestrator.execute_async(definition)

    assert result.status == SagaStatus.COMPENSATED
    assert bus_trace == ["create_ord-async-1", "cancel_ord-async-1"]


@pytest.mark.anyio
async def test_in_memory_saga_orchestrator_async_command_without_bus():
    """Verify async execution with Command but no bus returns COMPENSATED with error."""
    orchestrator = InMemorySagaOrchestrator(command_bus=None)
    definition = SagaDefinition(
        name="AsyncNoBusSaga",
        steps=(SagaStep(name="Step1", action=CreateOrderCmd(order_id="y")),),
    )

    result = await orchestrator.execute_async(definition)
    assert result.status == SagaStatus.COMPENSATED
    assert result.compensated is True
    assert "no CommandBusPort provided" in (result.error or "")
