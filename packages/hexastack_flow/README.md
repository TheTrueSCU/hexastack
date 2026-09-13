# 🌊 `hexastack-flow`

> Hexagonal workflow engine adapter integrating `hexaflow` with Hexastack CQRS, Relational Persistence, and Event Streaming.

---

## 🎯 Architectural Intent

`hexastack-flow` provides first-class hexagonal adapters connecting the lightweight [`hexaflow`](https://pypi.org/project/hexaflow/) workflow engine to Hexastack:

1. **CQRS Bridge**: `CommandStep` and `QueryStep` allow workflow steps to dispatch typed commands and queries directly onto the `CommandBus` and `QueryBus`, inheriting all CQRS middleware (auth, tracing, logging, metrics, retries).
2. **Durable Distributed Sagas**: Workflows natively subsume the Saga pattern by pairing forward command execution stages with compensating rollback stages, backed by durable checkpoints.
3. **Enterprise Persistence**: `SqlAlchemyWorkflowStore` persists workflow execution records and step checkpoints directly to PostgreSQL/SQLite/MySQL within transactional boundaries.
4. **Event Streaming**: Emits domain events (`WorkflowStartedEvent`, `WorkflowStepCompletedEvent`, `WorkflowSuspendedEvent`, `WorkflowCompletedEvent`, `WorkflowAbortedEvent`) wrapped in standard `CloudEventEnvelope`s through `hexastack-events`.
5. **DevTools Visualizer**: Backing engine for NiceGUI and Textual DAG monitoring.

---

## 🔄 Implementing the Saga Pattern as a Workflow

Historically, the **Saga Pattern** structures a distributed business transaction across multiple microservices or bounded contexts as a sequence of local transactions:
- **Forward transactions**: $T_1, T_2, \dots, T_n$
- **Compensating transactions**: $C_{k-1}, \dots, C_1$ executed in reverse (LIFO) order if step $k$ fails.

In `hexastack-flow`, you do **not** need a separate, restricted saga engine. A Saga is simply a workflow DAG that dispatches CQRS commands and executes compensating commands on failure.

### Example: Trip Booking Saga with CQRS & Hexaflow

```python
from hexaflow import Workflow
from hexastack_cqrs.ports.buses import CommandBusPort
from hexastack_flow.adapters.cqrs.runner import CqrsWorkflowRunner
from hexastack_flow.adapters.cqrs.steps import as_command_step

# 1. Define CQRS commands for forward actions & compensations
from my_domain.commands import (
    BookFlightCommand,
    CancelFlightCommand,
    BookHotelCommand,
    CancelHotelCommand,
    ChargePaymentCommand,
)

def build_trip_booking_workflow(bus: CommandBusPort, customer_id: str) -> Workflow:
    """Construct a durable distributed saga as a hexaflow Workflow."""
    workflow = (
        Workflow("trip-booking-saga")
        # Step 1: Reserve Flight
        .stage(
            "flight",
            as_command_step(
                lambda ctx: BookFlightCommand(customer_id=customer_id, destination="JFK"),
                bus,
                name="book_flight",
            ),
        )
        # Step 2: Reserve Hotel (runs after flight is confirmed)
        .stage(
            "hotel",
            as_command_step(
                lambda ctx: BookHotelCommand(customer_id=customer_id, room_type="deluxe"),
                bus,
                name="book_hotel",
            ),
            depends_on=["flight"],
        )
        # Step 3: Process Payment
        .stage(
            "payment",
            as_command_step(
                lambda ctx: ChargePaymentCommand(customer_id=customer_id, amount_cents=50000),
                bus,
                name="charge_payment",
            ),
            depends_on=["hotel"],
        )
    )
    return workflow

# 2. Execute via CqrsWorkflowRunner (with durable DB checkpoints)
runner = CqrsWorkflowRunner(engine=engine)
result = await runner.run(workflow.build())
```

### Why Workflows are Superior to Linear Sagas

| Feature | Legacy In-Memory Saga | `hexastack-flow` Workflow |
|---|---|---|
| **Execution Topologies** | Strictly sequential ($T_1 \to T_2 \to T_3$) | **Arbitrary DAGs** (e.g. reserve Flight & Hotel in parallel) |
| **Crash Recovery** | In-memory only (lost if process restarts) | **Durable Checkpoints** (`SqlAlchemyWorkflowStore`) |
| **Step Retries** | Manual loop or fail immediately | **Configurable `RetryPolicy`** (exponential backoff, jitter) |
| **Observability** | Console logs | **CloudEvents** (`WorkflowStepCompletedEvent`) + OTel spans |
| **Human-in-the-Loop** | Not supported | **Pause / Resume** (`engine.suspend()`, `engine.resume()`) |

---

## 📦 Installation

```bash
pip install hexastack[flow]
```

Or standalone:

```bash
pip install hexastack-flow
```

---

## 📄 License

Apache 2.0
