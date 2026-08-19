import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from hexastack_cli.adapters.routing import (
    _to_kebab_case,
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


class CommandWithConflictFields(Command):
    output: str
    quiet: bool
    debug: bool
    correlation_id: str
    user_id: str
    tenant_id: str
    input: str


class RawScalarCommand(Command):
    msg: str


class NoneReturnCommand(Command):
    name: str


@pytest.mark.parametrize(
    ("input_name", "expected_kebab"),
    [
        ("CreateOrderCommand", "create-order"),
        ("GetUserByIdQuery", "get-user-by-id"),
        ("SendNotificationCmd", "send-notification"),
        ("FindActiveUsersQry", "find-active-users"),
        ("SimpleCommand", "simple"),
        ("HTTPRequestHandler", "http-request-handler"),
        ("XML2JSONConverter", "xml2-json-converter"),
    ],
)
def test_to_kebab_case(input_name: str, expected_kebab: str):
    """Verify all regex transforms and suffix strippers in _to_kebab_case."""
    assert _to_kebab_case(input_name) == expected_kebab


def test_register_cqrs_command_and_query(tmp_path: Path):
    captured_cid: list[str] = []
    captured_user: list[tuple[str | None, str | None]] = []

    handler_reg = HandlerRegistry()
    handler_reg.register(AddNumbersCommand, lambda cmd: SumDTO(result=cmd.a + cmd.b))
    handler_reg.register(
        PositionalCommand, lambda cmd: f"Processed {cmd.item_id}:{cmd.amount}"
    )
    handler_reg.register(MultiplyQuery, lambda qry: qry.x * qry.y)
    handler_reg.register(RawScalarCommand, lambda cmd: f"Scalar: {cmd.msg}")
    handler_reg.register(NoneReturnCommand, lambda cmd: None)

    def _conflict_handler(cmd: CommandWithConflictFields) -> dict[str, str]:
        return {
            "output": cmd.output,
            "quiet": str(cmd.quiet),
            "debug": str(cmd.debug),
            "correlation_id": cmd.correlation_id,
            "user_id": cmd.user_id,
            "tenant_id": cmd.tenant_id,
            "input": cmd.input,
        }

    handler_reg.register(CommandWithConflictFields, _conflict_handler)

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
    register_cqrs_command(app, CommandWithConflictFields, pipeline=pipeline)
    register_cqrs_command(app, RawScalarCommand, pipeline=pipeline)
    register_cqrs_command(app, NoneReturnCommand, pipeline=pipeline)

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

    # 5. Raw scalar with plain / json / default formats
    res_scalar_json = runner.invoke(
        app, ["raw-scalar", "--msg", "hello", "--output", "json"]
    )
    assert res_scalar_json.exit_code == 0
    assert '"Scalar: hello"' in res_scalar_json.stdout

    res_scalar_plain = runner.invoke(
        app, ["raw-scalar", "--msg", "hello", "--output", "plain"]
    )
    assert res_scalar_plain.exit_code == 0
    assert "Scalar: hello" in res_scalar_plain.stdout

    res_scalar_default = runner.invoke(app, ["raw-scalar", "--msg", "hello"])
    assert res_scalar_default.exit_code == 0
    assert "Scalar: hello" in res_scalar_default.stdout

    res_scalar_quiet = runner.invoke(app, ["raw-scalar", "--msg", "hello", "--quiet"])
    assert res_scalar_quiet.exit_code == 0
    assert "Scalar: hello" not in res_scalar_quiet.stdout

    # 6. None return command
    res_none = runner.invoke(app, ["none-return", "--name", "noop"])
    assert res_none.exit_code == 0

    # 7. Query execution
    res_qry = runner.invoke(app, ["multiply", "--x", "6", "--y", "7"])
    assert res_qry.exit_code == 0
    assert "42" in res_qry.stdout

    # 8. Error handling exit code 1 with and without --debug
    res_err = runner.invoke(app, ["failing", "--flag"])
    assert res_err.exit_code == 1
    assert (
        "Invalid operation" in res_err.stdout or "Invalid operation" in res_err.stderr
    )

    res_debug_err = runner.invoke(app, ["failing", "--flag", "--debug"])
    assert res_debug_err.exit_code == 1

    # 9. Correlation ID, User Context, Tenant ID forwarding
    res_trace = runner.invoke(
        app,
        [
            "trace",
            "--tag",
            "alpha",
            "--correlation-id",
            "test-corr-uuid-123",
            "--tenant-id",
            "tenant-corp",
        ],
    )
    assert res_trace.exit_code == 0
    assert "test-corr-uuid-123" in captured_cid
    assert ("cli-user", "tenant-corp") in captured_user

    # 10. File payload input via --input file path
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(json.dumps({"a": 40, "b": 60}))
    res_file_input = runner.invoke(app, ["add-numbers", "--input", str(payload_file)])
    assert res_file_input.exit_code == 0
    assert "100" in res_file_input.stdout

    # 11. Raw JSON string input via --input
    res_input = runner.invoke(app, ["add-numbers", "--input", '{"a": 100, "b": 200}'])
    assert res_input.exit_code == 0
    assert "300" in res_input.stdout

    # 12. Stdin input via --input -
    res_stdin = runner.invoke(
        app, ["add-numbers", "--input", "-"], input='{"a": 7, "b": 8}'
    )
    assert res_stdin.exit_code == 0
    assert "15" in res_stdin.stdout

    # 13. Model with existing control field names (bypasses universal control options)
    res_conflict = runner.invoke(
        app,
        [
            "command-with-conflict-fields",
            "--output",
            "custom_out",
            "--quiet",
            "--debug",
            "--correlation-id",
            "cid_custom",
            "--user-id",
            "uid_custom",
            "--tenant-id",
            "tid_custom",
            "--input",
            "custom_in",
        ],
    )
    assert res_conflict.exit_code == 0

    # 14. Asynchronous coroutine handler execution
    res_async = runner.invoke(app, ["async", "--value", "futuristic"])
    assert res_async.exit_code == 0
    assert "Async result: futuristic" in res_async.stdout
