from collections.abc import Callable

from hexastack_core.domain import Command, Generic
from hexastack_cqrs.infra.middleware.generic import GenericMiddleware


class SampleCommand(Command):
    text: str


class PassThroughMiddleware:
    def __init__(self) -> None:
        self.invoked = False

    def __call__[G: Generic, R](
        self, instance: G, next_call: Callable[[G], R]
    ) -> R:
        self.invoked = True
        return next_call(instance)


def test_generic_middleware_protocol():
    middleware: GenericMiddleware = PassThroughMiddleware()

    def handler(cmd: SampleCommand) -> str:
        return f"hello {cmd.text}"

    res = middleware(SampleCommand(text="world"), handler)
    assert res == "hello world"
