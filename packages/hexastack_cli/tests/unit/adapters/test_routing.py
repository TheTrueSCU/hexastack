import json

import typer
from hexastack_cli.adapters.routing import (
    register_cqrs_command,
    register_cqrs_query,
)
from hexastack_core.domain import Command, Generic, Query
from hexastack_core.utils.context import (
    get_correlation_id,
    get_user_context,
)
from hexastack_cqrs.adapters.buses.command.synchronous import (
    SynchronousCommandBus,
)
from hexastack_cqrs.adapters.buses.event.synchronous import (
    SynchronousEventBus,
)
from hexastack_cqrs.adapters.buses.query.synchronous import (
    SynchronousQueryBus,
)
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_cqrs.infra.registries.command import CommandRegistry
from hexastack_cqrs.infra.registries.handler import HandlerRegistry
from hexastack_cqrs.infra.registries.presenter import PresenterRegistry
from hexastack_cqrs.infra.registries.query import QueryRegistry
from typer.testing import CliRunner


class AddNumbersCommand(Command):
    a: int
    b: int = 10


class PositionalCommand(Command):
    item_id: str
    amount: int = 1


class SumDTO(Generic):
    result: int


class MultiplyQuery(Query[int]):
    x: int
    y: int


class FailingCommand(Command):
    flag: bool


class TraceCommand(Command):
    tag: str


class AsyncCommand(Command):
    value: str


def test_register_cqrs_command_and_query():
    captured_cid: list[str] = []
    captured_user: list[tuple[str | None, str | None]] = []

    handler_reg = HandlerRegistry()
    handler_reg.register(
        AddNumbersCommand, lambda cmd: SumDTO(result=cmd.a + cmd.b)
    )
    handler_reg.register(
        PositionalCommand, lambda cmd: f"Processed {cmd.item_id}:{cmd.amount}"
    )
    handler_reg.register(
        MultiplyQuery, lambda qry: qry.x * qry.y
    )

    def _fail_handler(cmd: FailingCommand) -> None:
        raise ValueError("Invalid operation")

    def _trace_handler(cmd: TraceCommand) -> str:
        captured_cid.append(get_correlation_id())
        u = get_user_context()
        captured_user.append((u.user_id if u else None, u.tenant_id if u else None))
        return f"Traced {cmd.tag}"

    async def _async_handler(cmd: AsyncCommand) -> str:
        return f"Async result: {cmd.value}"

    handler_reg.register(FailingCommand, _fail_handler)
    handler_reg.register(TraceCommand, _trace_handler)
    handler_reg.register(AsyncCommand, _async_handler)

    pipeline = ExecutionPipeline(
        command_bus=SynchronousCommandBus(handler_registry=handler_reg),
        query_bus=SynchronousQueryBus(handler_registry=handler_reg),
        event_bus=SynchronousEventBus(),
        command_registry=CommandRegistry(),
        query_registry=QueryRegistry(),
        handler_registry=handler_reg,
        presenter_registry=PresenterRegistry(),
    )

    app = typer.Typer()
    register_cqrs_command(app, AddNumbersCommand, pipeline=pipeline)
    register_cqrs_command(
        app,
        PositionalCommand,
        pipeline=pipeline,
        name="pos-cmd",
        positional=["item_id"],
    )
    register_cqrs_query(app, MultiplyQuery, pipeline=pipeline)
    register_cqrs_command(app, FailingCommand, pipeline=pipeline)
    register_cqrs_command(app, TraceCommand, pipeline=pipeline)
    register_cqrs_command(app, AsyncCommand, pipeline=pipeline)

    runner = CliRunner()

    # 1. Standard table output
    res_cmd = runner.invoke(app, ["add-numbers", "--a", "5"])
    assert res_cmd.exit_code == 0
    assert "SumDTO" in res_cmd.stdout or "15" in res_cmd.stdout

    # 2. Positional argument: app pos-cmd item-123 --amount 4
    res_pos = runner.invoke(app, ["pos-cmd", "item-123", "--amount", "4"])
    assert res_pos.exit_code == 0
    assert "Processed item-123:4" in res_pos.stdout

    # 3. JSON output (CI / pipe friendly)
    res_json = runner.invoke(app, ["add-numbers", "--a", "5", "--output", "json"])
    assert res_json.exit_code == 0
    parsed = json.loads(res_json.stdout)
    assert parsed == {"result": 15}

    # 4. Plain TSV output
    res_plain = runner.invoke(app, ["add-numbers", "--a", "5", "-o", "plain"])
    assert res_plain.exit_code == 0
    assert "result\t15" in res_plain.stdout

    # 5. Query
    res_qry = runner.invoke(app, ["multiply", "--x", "6", "--y", "7"])
    assert res_qry.exit_code == 0
    assert "42" in res_qry.stdout

    # 6. Error handling exit code 1 with and without --debug
    res_err = runner.invoke(app, ["failing", "--flag"])
    assert res_err.exit_code == 1
    assert "Invalid operation" in res_err.stdout or "Invalid operation" in res_err.stderr

    res_debug_err = runner.invoke(app, ["failing", "--flag", "--debug"])
    assert res_debug_err.exit_code == 1

    # 7. Correlation ID, User Context, Tenant ID forwarding
    res_trace = runner.invoke(
        app,
        [
            "trace",
            "--tag",
            "alpha",
            "--correlation-id",
            "test-corr-uuid-123",
            "--user-id",
            "usr-99",
            "--tenant-id",
            "tenant-corp",
        ],
    )
    assert res_trace.exit_code == 0
    assert "test-corr-uuid-123" in captured_cid
    assert ("usr-99", "tenant-corp") in captured_user

    # 8. Raw JSON payload input via --input
    res_input = runner.invoke(
        app, ["add-numbers", "--input", '{"a": 100, "b": 200}']
    )
    assert res_input.exit_code == 0
    assert "300" in res_input.stdout

    # 9. Asynchronous coroutine handler execution
    res_async = runner.invoke(app, ["async", "--value", "futuristic"])
    assert res_async.exit_code == 0
    assert "Async result: futuristic" in res_async.stdout
