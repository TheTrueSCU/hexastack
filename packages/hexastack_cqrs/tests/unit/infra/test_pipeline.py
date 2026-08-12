from typing import Any

import pytest
from hexastack_core.domain import Command, Event, Generic, Query
from hexastack_core.infra import ExceptionRegistry
from hexastack_core.ports import Presenter
from hexastack_cqrs.adapters.buses import SynchronousEventBus
from hexastack_cqrs.infra.pipeline import (
    AmbiguousMessageError,
    ExecutionPipeline,
    PipelineError,
    UnregisteredMessageError,
)
from hexastack_cqrs.infra.registries import (
    CommandRegistry,
    HandlerRegistry,
    PresenterRegistry,
    QueryRegistry,
)


class CreateUser(Command):
    user_id: str
    name: str


class GetUser(Query[dict[str, str]]):
    user_id: str


class UserCreated(Event):
    user_id: str


class UserDTO(Generic):
    user_id: str
    name: str


class JsonUserPresenter(Presenter):
    def present(self, instance: Generic) -> Any | None:
        if isinstance(instance, UserDTO):
            return {"id": instance.user_id, "fullName": instance.name}
        return None


def test_pipeline_execute_command():
    handler_reg = HandlerRegistry()
    handler_reg.register(
        CreateUser, lambda cmd: UserDTO(user_id=cmd.user_id, name=cmd.name)
    )

    pipeline = ExecutionPipeline(handler_registry=handler_reg)
    result = pipeline.execute(CreateUser(user_id="u1", name="Alice"))

    assert isinstance(result, UserDTO)
    assert result.user_id == "u1"
    assert result.name == "Alice"


def test_pipeline_execute_query():
    handler_reg = HandlerRegistry()
    handler_reg.register(
        GetUser, lambda qry: UserDTO(user_id=qry.user_id, name="FoundUser")
    )

    pipeline = ExecutionPipeline(handler_registry=handler_reg)
    result = pipeline.execute(GetUser(user_id="u2"))

    assert isinstance(result, UserDTO)
    assert result.user_id == "u2"


def test_pipeline_execute_event():
    event_bus = SynchronousEventBus()
    pipeline = ExecutionPipeline(
        handler_registry=HandlerRegistry(),
        event_bus=event_bus,
    )
    event_logs: list[str] = []

    event_bus.subscribe(
        UserCreated, lambda evt: event_logs.append(evt.user_id)
    )
    result = pipeline.execute(UserCreated(user_id="u-evt"))

    assert result is None
    assert event_logs == ["u-evt"]


def test_pipeline_execute_with_presenter():
    handler_reg = HandlerRegistry()
    handler_reg.register(
        CreateUser, lambda cmd: UserDTO(user_id=cmd.user_id, name=cmd.name)
    )

    presenter_reg = PresenterRegistry()
    presenter_reg.register(UserDTO, "json", JsonUserPresenter())

    pipeline = ExecutionPipeline(
        handler_registry=handler_reg,
        presenter_registry=presenter_reg,
    )

    presented = pipeline.execute(
        CreateUser(user_id="u3", name="Charlie"), output_format="json"
    )
    assert presented == {"id": "u3", "fullName": "Charlie"}


def test_pipeline_exception_handling():
    handler_reg = HandlerRegistry()

    def failing_handler(cmd: CreateUser) -> None:
        raise ValueError("Invalid user state")

    handler_reg.register(CreateUser, failing_handler)

    exc_reg = ExceptionRegistry()
    exc_reg.register(ValueError, lambda exc: {"error": str(exc), "status": 400})

    pipeline = ExecutionPipeline(
        handler_registry=handler_reg,
        exception_registry=exc_reg,
    )

    error_response = pipeline.execute(CreateUser(user_id="u4", name="ErrorUser"))
    assert error_response == {"error": "Invalid user state", "status": 400}


def test_pipeline_execute_by_name():
    cmd_reg = CommandRegistry()
    cmd_reg.register(CreateUser)

    query_reg = QueryRegistry()
    query_reg.register(GetUser)

    handler_reg = HandlerRegistry()
    handler_reg.register(
        CreateUser, lambda cmd: UserDTO(user_id=cmd.user_id, name=cmd.name)
    )
    handler_reg.register(
        GetUser, lambda qry: UserDTO(user_id=qry.user_id, name="Found")
    )

    pipeline = ExecutionPipeline(
        handler_registry=handler_reg,
        command_registry=cmd_reg,
        query_registry=query_reg,
    )

    cmd_res = pipeline.execute_by_name(
        "CreateUser", {"user_id": "u5", "name": "Eve"}
    )
    assert isinstance(cmd_res, UserDTO)
    assert cmd_res.user_id == "u5"

    qry_res = pipeline.execute_by_name("GetUser", {"user_id": "u5"})
    assert isinstance(qry_res, UserDTO)
    assert qry_res.user_id == "u5"


def test_pipeline_execute_by_name_ambiguity_error():
    cmd_reg = CommandRegistry()
    query_reg = QueryRegistry()

    class Ambiguous(Command):
        id: str

    class AmbiguousQuery(Query[str]):
        id: str

    cmd_reg.register_by_name(Ambiguous, "AmbiguousItem")
    query_reg.register_by_name(AmbiguousQuery, "AmbiguousItem")

    pipeline = ExecutionPipeline(
        handler_registry=HandlerRegistry(),
        command_registry=cmd_reg,
        query_registry=query_reg,
    )

    with pytest.raises(AmbiguousMessageError) as exc_info:
        pipeline.execute_by_name("AmbiguousItem", {"id": "1"})

    assert isinstance(exc_info.value, PipelineError)
    assert "Ambiguous message name 'AmbiguousItem'" in str(exc_info.value)


def test_pipeline_execute_by_name_unregistered_error():
    pipeline = ExecutionPipeline(handler_registry=HandlerRegistry())

    with pytest.raises(UnregisteredMessageError) as exc_info:
        pipeline.execute_by_name("Missing", {})

    assert isinstance(exc_info.value, PipelineError)
    assert "No Command or Query registered with name 'Missing'" in str(exc_info.value)
