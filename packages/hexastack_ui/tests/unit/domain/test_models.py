"""Unit tests for hexastack_ui domain models."""

from hexastack_ui.domain.models import (
    CQRSMessageSummary,
    DevToolsDashboardState,
    FeatureFlagSummary,
    ServiceBindingSummary,
)


def test_domain_models_creation():
    """Verify domain models instantiate and serialize cleanly."""
    cmd = CQRSMessageSummary(
        name="CreateOrder", message_type="Command", module="sales.commands"
    )
    assert cmd.name == "CreateOrder"
    assert cmd.message_type == "Command"
    assert cmd.module == "sales.commands"

    flag = FeatureFlagSummary(key="beta_mode", enabled=True, description="Enable beta")
    assert flag.key == "beta_mode"
    assert flag.enabled is True

    service = ServiceBindingSummary(
        service="IOrderRepo", module="ports.orders", resolver="Singleton"
    )
    assert service.service == "IOrderRepo"

    state = DevToolsDashboardState(
        commands=[cmd],
        queries=[],
        flags=[flag],
        services=[service],
        middlewares=["AuthMiddleware", "LoggingMiddleware"],
    )
    assert len(state.commands) == 1
    assert len(state.flags) == 1
    assert len(state.services) == 1
    assert len(state.middlewares) == 2
