"""Unit tests for WorkflowEventPublisher adapter.

Notes/Architectural Intent:
    Verifies that WorkflowEventPublisher formats and broadcasts domain events
    over the injected EventBusPort.
"""

from unittest.mock import MagicMock

from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_flow.adapters.events.publisher import WorkflowEventPublisher
from hexastack_flow.domain.events import (
    WorkflowAbortedEvent,
    WorkflowCompletedEvent,
    WorkflowStartedEvent,
    WorkflowStepCompletedEvent,
    WorkflowSuspendedEvent,
)


def test_publisher_methods() -> None:
    """Validate all event broadcast methods dispatch correct domain event types."""
    mock_bus = MagicMock(spec=EventBusPort)
    publisher = WorkflowEventPublisher(mock_bus)

    # 1. Started
    publisher.publish_started("run-1", "order_wf")
    assert mock_bus.publish.call_count == 1
    evt1 = mock_bus.publish.call_args[0][0]
    assert isinstance(evt1, WorkflowStartedEvent)
    assert evt1.run_id == "run-1"

    # 2. Step Completed
    publisher.publish_step_completed(
        run_id="run-1",
        stage_name="validation",
        step_name="verify_email",
        attempt_number=1,
        duration_seconds=0.05,
        output_summary={"valid": True},
    )
    assert mock_bus.publish.call_count == 2
    evt2 = mock_bus.publish.call_args[0][0]
    assert isinstance(evt2, WorkflowStepCompletedEvent)
    assert evt2.step_name == "verify_email"
    assert evt2.output_summary == {"valid": True}

    # 3. Suspended
    publisher.publish_suspended(
        run_id="run-1",
        stage_name="payment",
        step_name="charge",
        error_type="PaymentGatewayError",
        error_message="Card declined",
    )
    assert mock_bus.publish.call_count == 3
    evt3 = mock_bus.publish.call_args[0][0]
    assert isinstance(evt3, WorkflowSuspendedEvent)
    assert evt3.error_type == "PaymentGatewayError"

    # 4. Completed
    publisher.publish_completed("run-1", "order_wf", total_steps=5)
    assert mock_bus.publish.call_count == 4
    evt4 = mock_bus.publish.call_args[0][0]
    assert isinstance(evt4, WorkflowCompletedEvent)
    assert evt4.total_steps == 5

    # 5. Aborted
    publisher.publish_aborted("run-1", "order_wf", reason="Fraud check failed")
    assert mock_bus.publish.call_count == 5
    evt5 = mock_bus.publish.call_args[0][0]
    assert isinstance(evt5, WorkflowAbortedEvent)
    assert evt5.reason == "Fraud check failed"
