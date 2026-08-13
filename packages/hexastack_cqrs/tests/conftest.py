from collections.abc import Callable

import pytest
from hexastack_core.infra import ExceptionRegistry
from hexastack_cqrs.infra.pipeline import ExecutionPipeline, create_pipeline
from hexastack_cqrs.infra.registries import (
    CommandRegistry,
    HandlerRegistry,
    PresenterRegistry,
    QueryRegistry,
)
from hexastack_cqrs.ports.buses import (
    CommandBusPort,
    EventBusPort,
    QueryBusPort,
)


@pytest.fixture
def create_pipeline_fixture() -> Callable[..., ExecutionPipeline]:
    """Factory fixture to create an ExecutionPipeline with optional custom registries/buses.

    Returns:
        Callable factory returning configured ExecutionPipeline.
    """

    def _factory(
        handler_registry: HandlerRegistry | None = None,
        command_registry: CommandRegistry | None = None,
        query_registry: QueryRegistry | None = None,
        presenter_registry: PresenterRegistry | None = None,
        exception_registry: ExceptionRegistry | None = None,
        command_bus: CommandBusPort | None = None,
        query_bus: QueryBusPort | None = None,
        event_bus: EventBusPort | None = None,
    ) -> ExecutionPipeline:
        return create_pipeline(
            handler_registry=handler_registry,
            command_registry=command_registry,
            query_registry=query_registry,
            presenter_registry=presenter_registry,
            exception_registry=exception_registry,
            command_bus=command_bus,
            query_bus=query_bus,
            event_bus=event_bus,
        )

    return _factory


@pytest.fixture
def clean_pipeline(
    create_pipeline_fixture: Callable[..., ExecutionPipeline],
) -> ExecutionPipeline:
    """Fixture providing a fresh default ExecutionPipeline instance."""
    return create_pipeline_fixture()
