from typing import Any

from pydantic import BaseModel

from hexastack_core.domain import Command, Event, Generic, Query
from hexastack_cqrs.infra.decorators import (
    ConfigMetadata,
    ExceptionMetadata,
    HandlerMetadata,
    PresenterMetadata,
    command_handler,
    config_section,
    event_listener,
    exception_handler,
    presenter,
    query_handler,
)


class SampleCommand(Command):
    id: str


class SampleQuery(Query[str]):
    id: str


class SampleEvent(Event):
    id: str


class SampleDTO(Generic):
    id: str


class CustomAppError(Exception):
    pass


def test_command_handler_decorator():
    @command_handler(SampleCommand)
    def handle_cmd(cmd: SampleCommand) -> str:
        return cmd.id

    meta = getattr(handle_cmd, "__hexastack_handler__", None)
    assert isinstance(meta, HandlerMetadata)
    assert meta.kind == "command"
    assert meta.target_cls == SampleCommand
    assert handle_cmd(SampleCommand(id="c1")) == "c1"


def test_config_section_decorator():
    @config_section("app.database")
    class DbConfig(BaseModel):
        url: str = "sqlite:///:memory:"

    meta = getattr(DbConfig, "__hexastack_handler__", None)
    assert isinstance(meta, ConfigMetadata)
    assert meta.section_name == "app.database"


def test_event_listener_decorator():
    @event_listener(SampleEvent)
    def handle_evt(evt: SampleEvent) -> None:
        pass

    meta = getattr(handle_evt, "__hexastack_handler__", None)
    assert isinstance(meta, HandlerMetadata)
    assert meta.kind == "event"
    assert meta.target_cls == SampleEvent


def test_exception_handler_decorator():
    @exception_handler(CustomAppError)
    def handle_custom_err(exc: CustomAppError) -> dict[str, str]:
        return {"error": str(exc)}

    meta = getattr(handle_custom_err, "__hexastack_handler__", None)
    assert isinstance(meta, ExceptionMetadata)
    assert meta.target_cls == CustomAppError


def test_presenter_decorator():
    @presenter(SampleDTO, "json")
    class JsonPresenter:
        def present(self, instance: Generic) -> Any | None:
            return {"id": getattr(instance, "id", "")}

    meta = getattr(JsonPresenter, "__hexastack_handler__", None)
    assert isinstance(meta, PresenterMetadata)
    assert meta.target_cls == SampleDTO
    assert meta.output_format == "json"


def test_query_handler_decorator():
    @query_handler(SampleQuery)
    def handle_qry(qry: SampleQuery) -> str:
        return qry.id

    meta = getattr(handle_qry, "__hexastack_handler__", None)
    assert isinstance(meta, HandlerMetadata)
    assert meta.kind == "query"
    assert meta.target_cls == SampleQuery
    assert handle_qry(SampleQuery(id="q1")) == "q1"
