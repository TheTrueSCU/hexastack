from __future__ import annotations

import pytest

from hexastack_core.domain import Command, Event, Generic, Query
from hexastack_core.infra.container import MicroContainer
from hexastack_cqrs.infra.edge import EdgeExecutionProfile, create_edge_pipeline
from hexastack_cqrs.ports.buses import CommandBusPort, EventBusPort, QueryBusPort
from hexastack_cqrs.ports.pipeline import ExecutionPipelinePort


class EdgePingCommand(Command):
    payload: str


class EdgeEchoQuery(Query[str]):
    query_text: str


class EdgeNotificationEvent(Event):
    topic: str


class EdgeCustomGeneric(Generic):
    detail: str


def test_edge_execution_profile_defaults():
    profile = EdgeExecutionProfile()

    cmd_bus = profile.container.resolve(CommandBusPort)
    assert cmd_bus is profile.command_bus

    query_bus = profile.container.resolve(QueryBusPort)
    assert query_bus is profile.query_bus

    event_bus = profile.container.resolve(EventBusPort)
    assert event_bus is profile.event_bus

    pipeline = profile.container.resolve(ExecutionPipelinePort)
    assert pipeline is profile.pipeline


def test_create_edge_pipeline_factory():
    custom_container = MicroContainer()
    profile = create_edge_pipeline(container=custom_container)

    assert profile.container is custom_container
    cmd_bus = custom_container.resolve(CommandBusPort)
    assert cmd_bus is profile.command_bus


def test_edge_pipeline_dispatch_command():
    profile = EdgeExecutionProfile()

    def handle_ping(cmd: EdgePingCommand) -> str:
        return f"pong:{cmd.payload}"

    chained = profile.register_handler(EdgePingCommand, handle_ping)
    assert chained is profile

    result = profile.dispatch(EdgePingCommand(payload="test-data"))
    assert result == "pong:test-data"


@pytest.mark.asyncio
async def test_edge_pipeline_dispatch_async_command():
    profile = EdgeExecutionProfile()

    def handle_ping(cmd: EdgePingCommand) -> str:
        return f"async-pong:{cmd.payload}"

    profile.register_handler(EdgePingCommand, handle_ping)

    result = await profile.dispatch_async(EdgePingCommand(payload="edge-async"))
    assert result == "async-pong:edge-async"


def test_edge_pipeline_dispatch_query():
    profile = EdgeExecutionProfile()

    def handle_echo(query: EdgeEchoQuery) -> str:
        return f"echo:{query.query_text}"

    profile.register_handler(EdgeEchoQuery, handle_echo)

    result = profile.dispatch(EdgeEchoQuery(query_text="hello edge"))
    assert result == "echo:hello edge"


@pytest.mark.asyncio
async def test_edge_pipeline_dispatch_async_query():
    profile = EdgeExecutionProfile()

    def handle_echo(query: EdgeEchoQuery) -> str:
        return f"async-echo:{query.query_text}"

    profile.register_handler(EdgeEchoQuery, handle_echo)

    result = await profile.dispatch_async(EdgeEchoQuery(query_text="hello async"))
    assert result == "async-echo:hello async"


def test_edge_pipeline_event_publishing():
    profile = EdgeExecutionProfile()
    received_topics: list[str] = []

    def on_event(event: EdgeNotificationEvent) -> None:
        received_topics.append(event.topic)

    profile.register_handler(EdgeNotificationEvent, on_event)

    res = profile.dispatch(EdgeNotificationEvent(topic="sensor/temperature"))
    assert res is None
    assert received_topics == ["sensor/temperature"]


@pytest.mark.asyncio
async def test_edge_pipeline_async_event_publishing():
    profile = EdgeExecutionProfile()
    received_topics: list[str] = []

    def on_event(event: EdgeNotificationEvent) -> None:
        received_topics.append(event.topic)

    profile.register_handler(EdgeNotificationEvent, on_event)

    res = await profile.dispatch_async(EdgeNotificationEvent(topic="sensor/humidity"))
    assert res is None
    assert received_topics == ["sensor/humidity"]
