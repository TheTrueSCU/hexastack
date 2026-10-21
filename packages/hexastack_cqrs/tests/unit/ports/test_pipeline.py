from typing import Any

from hexastack_core.domain import Command, Generic, Query
from hexastack_cqrs.ports.pipeline import ExecutionPipelinePort


class SampleCommand(Command):
    message: str


class SampleQuery(Query[str]):
    query_id: str


class MockPipeline(ExecutionPipelinePort):
    def __init__(self) -> None:
        self.commands: dict[str, type[Command]] = {"SampleCommand": SampleCommand}
        self.queries: dict[str, type[Query[Any]]] = {"SampleQuery": SampleQuery}

    def execute(
        self,
        instance: Generic,
        output_format: str | None = None,
    ) -> Any:
        return {"executed": instance.__class__.__name__, "format": output_format}

    def execute_by_name(
        self,
        name: str,
        payload: dict[str, Any],
        output_format: str | None = None,
    ) -> Any:
        cls = self.commands.get(name) or self.queries.get(name)
        if not cls:
            raise ValueError(f"Unknown message: {name}")
        instance = cls.model_validate(payload)
        return self.execute(instance, output_format=output_format)

    def get_registered_commands(self) -> dict[str, type[Command]]:
        return dict(self.commands)

    def get_registered_queries(self) -> dict[str, type[Query[Any]]]:
        return dict(self.queries)


def test_execution_pipeline_port_interface():
    pipeline = MockPipeline()

    # Test inspection methods
    cmds = pipeline.get_registered_commands()
    assert "SampleCommand" in cmds
    assert cmds["SampleCommand"] is SampleCommand

    queries = pipeline.get_registered_queries()
    assert "SampleQuery" in queries
    assert queries["SampleQuery"] is SampleQuery

    # Test execution methods
    res = pipeline.execute(SampleCommand(message="hello"), output_format="json")
    assert res == {"executed": "SampleCommand", "format": "json"}

    by_name = pipeline.execute_by_name("SampleCommand", {"message": "dynamic"})
    assert by_name == {"executed": "SampleCommand", "format": None}


def test_execution_pipeline_port_abstract_methods():
    abstracts = ExecutionPipelinePort.__abstractmethods__
    assert "execute" in abstracts
    assert "execute_by_name" in abstracts
    assert "get_registered_commands" in abstracts
    assert "get_registered_queries" in abstracts
