from typing import Any

import pytest

from hexastack_core.domain import Command, Event, Generic, Query
from hexastack_core.infra import ExceptionRegistry
from hexastack_core.ports.presenter import PresenterPort
from hexastack_cqrs.adapters.buses import SynchronousEventBus
from hexastack_cqrs.infra.pipeline import (
    AmbiguousMessageError,
    ExecutionPipeline,
    PipelineError,
    UnregisteredMessageError,
    create_pipeline,
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


class CustomGenericMessage(Generic):
    payload_val: int


class JsonUserPresenter(PresenterPort):
    def present(self, instance: Generic) -> Any | None:
        if isinstance(instance, UserDTO):
            return {"id": instance.user_id, "fullName": instance.name}
        return None


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


def test_pipeline_execute_by_name_and_create_pipeline():
    cmd_reg = CommandRegistry()
    cmd_reg.register(CreateUser)

    query_reg = QueryRegistry()
    query_reg.register(GetUser)

    pres_reg = PresenterRegistry()
    pres_reg.register(UserDTO, "json", JsonUserPresenter())

    handler_reg = HandlerRegistry()
    handler_reg.register(
        CreateUser, lambda cmd: UserDTO(user_id=cmd.user_id, name=cmd.name)
    )
    handler_reg.register(
        GetUser, lambda qry: UserDTO(user_id=qry.user_id, name="Found")
    )

    pipeline = create_pipeline(
        handler_registry=handler_reg,
        command_registry=cmd_reg,
        query_registry=query_reg,
        presenter_registry=pres_reg,
    )

    cmd_res = pipeline.execute_by_name(
        "CreateUser",
        {"user_id": "u5", "name": "Eve"},
        output_format="json",
    )
    assert cmd_res == {"id": "u5", "fullName": "Eve"}

    qry_res = pipeline.execute_by_name("GetUser", {"user_id": "u5"})
    assert isinstance(qry_res, UserDTO)
    assert qry_res.user_id == "u5"


def test_pipeline_execute_by_name_unregistered_error():
    pipeline = ExecutionPipeline(handler_registry=HandlerRegistry())

    with pytest.raises(UnregisteredMessageError) as exc_info:
        pipeline.execute_by_name("Missing", {})

    assert isinstance(exc_info.value, PipelineError)
    assert "No Command or Query registered with name 'Missing'" in str(exc_info.value)


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


def test_pipeline_execute_event():
    event_bus = SynchronousEventBus()
    received = []
    event_bus.subscribe(UserCreated, lambda evt: received.append(evt.user_id))

    pipeline = ExecutionPipeline(
        handler_registry=HandlerRegistry(), event_bus=event_bus
    )
    result = pipeline.execute(UserCreated(user_id="u3"))

    assert result is None
    assert received == ["u3"]


def test_pipeline_execute_generic_fallback():
    handler_reg = HandlerRegistry()
    handler_reg.register(
        CustomGenericMessage, lambda msg: f"processed:{msg.payload_val}"
    )

    pipeline = ExecutionPipeline(handler_registry=handler_reg)
    result = pipeline.execute(CustomGenericMessage(payload_val=42))
    assert result == "processed:42"


def test_pipeline_execute_query():
    handler_reg = HandlerRegistry()
    handler_reg.register(GetUser, lambda qry: {"id": qry.user_id, "status": "active"})

    pipeline = ExecutionPipeline(handler_registry=handler_reg)
    result = pipeline.execute(GetUser(user_id="u2"))

    assert result == {"id": "u2", "status": "active"}


def test_pipeline_execute_with_exception_registry():
    handler_reg = HandlerRegistry()

    def _failing_handler(cmd):
        raise ValueError("Invalid user state")

    handler_reg.register(CreateUser, _failing_handler)

    exc_reg = ExceptionRegistry()
    exc_reg.register(ValueError, lambda err: {"error": str(err), "status": 400})

    pipeline = ExecutionPipeline(
        handler_registry=handler_reg,
        exception_registry=exc_reg,
    )

    error_response = pipeline.execute(CreateUser(user_id="u4", name="ErrorUser"))
    assert error_response == {"error": "Invalid user state", "status": 400}


def test_pipeline_execute_with_presenter():
    handler_reg = HandlerRegistry()
    handler_reg.register(
        CreateUser, lambda cmd: UserDTO(user_id=cmd.user_id, name=cmd.name)
    )

    pres_reg = PresenterRegistry()
    pres_reg.register(UserDTO, "json", JsonUserPresenter())

    pipeline = ExecutionPipeline(
        handler_registry=handler_reg,
        presenter_registry=pres_reg,
    )

    presented = pipeline.execute(
        CreateUser(user_id="u1", name="Alice"), output_format="json"
    )
    assert presented == {"id": "u1", "fullName": "Alice"}
