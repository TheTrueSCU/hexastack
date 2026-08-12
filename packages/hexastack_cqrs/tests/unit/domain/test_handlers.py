from hexastack_core.domain import Command, Event, Query
from hexastack_cqrs.domain.handlers import (
    CommandHandler,
    EventHandler,
    QueryHandler,
)


class SampleCommand(Command):
    message: str


class SampleEvent(Event):
    event_id: str


class SampleQuery(Query[int]):
    factor: int


class SampleCommandHandler(CommandHandler[SampleCommand, str]):
    def handle(self, item: SampleCommand) -> str:
        return f"Handled: {item.message}"


class SampleEventHandler(EventHandler[SampleEvent]):
    def __init__(self) -> None:
        self.handled: list[str] = []

    def handle(self, item: SampleEvent) -> None:
        self.handled.append(item.event_id)


class SampleQueryHandler(QueryHandler[SampleQuery, int]):
    def handle(self, item: SampleQuery) -> int:
        return item.factor * 10


def test_handlers():
    cmd_handler = SampleCommandHandler()
    assert cmd_handler.handle(SampleCommand(message="hi")) == "Handled: hi"

    evt_handler = SampleEventHandler()
    evt_handler.handle(SampleEvent(event_id="e-1"))
    assert evt_handler.handled == ["e-1"]

    query_handler = SampleQueryHandler()
    assert query_handler.handle(SampleQuery(factor=5)) == 50
