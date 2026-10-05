"""Unit tests for FlowBootstrapper.

Notes/Architectural Intent:
    Verifies that FlowBootstrapper wires CqrsWorkflowOrchestratorPort into
    the dependency injection container during application bootstrap.
"""

from unittest.mock import MagicMock

from rodi import Container

from hexastack_core.infra.bootstrap import BootstrapContext
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_flow.infra.bootstrap import FlowBootstrapper
from hexastack_flow.ports.orchestrator import CqrsWorkflowOrchestratorPort


def test_flow_bootstrapper_configure() -> None:
    """Ensure FlowBootstrapper registers CqrsWorkflowOrchestratorPort in container."""
    container = Container()
    mock_event_bus = MagicMock(spec=EventBusPort)
    container.add_instance(mock_event_bus, declared_class=EventBusPort)

    context = BootstrapContext(
        container=container,
        config=None,
        config_registry=ConfigRegistry(),
    )

    bootstrapper = FlowBootstrapper()
    bootstrapper.configure(context)

    # Validate registration
    assert CqrsWorkflowOrchestratorPort in container
    orchestrator = container.resolve(CqrsWorkflowOrchestratorPort)
    assert orchestrator is not None
    assert context.properties.get("flow_runner") is not None


def test_flow_bootstrapper_register_config() -> None:
    """Ensure register_config executes cleanly."""
    bootstrapper = FlowBootstrapper()
    mock_registry = MagicMock()
    bootstrapper.register_config(mock_registry)
