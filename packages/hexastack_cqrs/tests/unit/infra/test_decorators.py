from typing import Any

from pydantic import BaseModel

from hexastack_core.domain import Command, Event, Generic, Query
from hexastack_cqrs.infra.decorators import (
    ConfigMetadata,
    ExceptionMetadata,
    HandlerMetadata,
    PresenterMetadata,
    SagaMetadata,
    command_handler,
    config_section,
    event_listener,
    exception_handler,
    presenter,
    query_handler,
    saga,
    step,
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
    res = handle_qry(SampleQuery(id="q1"))
    assert res == "q1"


def test_saga_decorator_pattern_a_function() -> None:
    """Verify @saga on functional workflow definition (Pattern A)."""

    @saga(name="FuncSaga", trigger=SampleCommand)
    def my_saga(cmd: SampleCommand) -> None:
        pass

    meta = getattr(my_saga, "__hexastack_saga__", None)
    assert isinstance(meta, SagaMetadata)
    assert meta.name == "FuncSaga"
    assert meta.trigger == SampleCommand
    assert meta.is_class is False


def test_saga_decorator_pattern_b_class() -> None:
    """Verify @saga on class with @step methods (Pattern B)."""
    trace: list[str] = []

    @saga(name="ClassWorkflowSaga", trigger=SampleCommand)
    class BookingSaga:
        @step(name="Step1", order=1, compensate="rollback_step1")
        def forward1(self, cmd: SampleCommand) -> str:
            trace.append("f1")
            return f"f1_{cmd.id}"

        def rollback_step1(self, res: str) -> None:
            trace.append(f"comp1_{res}")

        @step(name="Step2", order=2)
        def forward2(self, cmd: SampleCommand) -> str:
            trace.append("f2")
            return "f2_done"

    meta = getattr(BookingSaga, "__hexastack_saga__", None)
    assert isinstance(meta, SagaMetadata)
    assert meta.name == "ClassWorkflowSaga"
    assert meta.trigger == SampleCommand
    assert meta.is_class is True

    instance = BookingSaga()
    instance_any: Any = instance
    saga_def = instance_any.build_saga(SampleCommand(id="c99"))
    assert saga_def.name == "ClassWorkflowSaga"
    assert len(saga_def.steps) == 2
    assert saga_def.steps[0].name == "Step1"
    assert saga_def.steps[1].name == "Step2"


def test_saga_decorator_class_without_steps_raises_error() -> None:
    """Verify class with no @step methods raises ValueError."""
    import pytest

    with pytest.raises(
        ValueError, match="must define at least one method decorated with @step"
    ):

        @saga(name="EmptySaga")
        class EmptySaga:
            def plain_method(self) -> None:
                pass


def test_saga_decorator_class_with_missing_compensate_raises_error() -> None:
    """Verify step referencing non-existent compensation method raises ValueError."""
    import pytest

    @saga(name="BrokenSaga")
    class BrokenSaga:
        @step(name="Step1", order=1, compensate="nonexistent_method")
        def forward(self) -> None:
            pass

    instance = BrokenSaga()
    instance_any: Any = instance
    with pytest.raises(ValueError, match="references non-existent compensation method"):
        instance_any.build_saga()
