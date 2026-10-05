from collections.abc import Callable

import pytest

from hexastack_core.adapters.ai import InMemoryLlmProvider
from hexastack_cqrs.infra.pipeline import ExecutionPipeline, create_pipeline
from hexastack_cqrs.infra.registries import (
    CommandRegistry,
    HandlerRegistry,
    PresenterRegistry,
    QueryRegistry,
)


@pytest.fixture
def clean_pipeline(
    create_pipeline_fixture: Callable[..., ExecutionPipeline],
) -> ExecutionPipeline:
    """Fixture providing a fresh default ExecutionPipeline instance."""
    return create_pipeline_fixture()


@pytest.fixture
def create_pipeline_fixture() -> Callable[..., ExecutionPipeline]:
    """Factory fixture to create an ExecutionPipeline with custom or clean registries."""

    def _factory(
        handler_registry: HandlerRegistry | None = None,
        command_registry: CommandRegistry | None = None,
        query_registry: QueryRegistry | None = None,
        presenter_registry: PresenterRegistry | None = None,
    ) -> ExecutionPipeline:
        return create_pipeline(
            handler_registry=handler_registry,
            command_registry=command_registry,
            query_registry=query_registry,
            presenter_registry=presenter_registry,
        )

    return _factory


@pytest.fixture
def mock_llm() -> InMemoryLlmProvider:
    """Fixture providing a clean InMemoryLlmProvider instance for tests."""
    return InMemoryLlmProvider()
