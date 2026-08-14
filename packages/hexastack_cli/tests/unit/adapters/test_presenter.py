import json
from io import StringIO

from rich.console import Console

from hexastack_cli.adapters.presenter import RichTerminalPresenter
from hexastack_core.domain import Generic


class SampleOutput(Generic):
    name: str
    age: int


class ListOutput(Generic):
    tags: list[str]


def test_rich_terminal_presenter_table():
    buf = StringIO()
    console = Console(file=buf, color_system=None, width=80)
    presenter = RichTerminalPresenter(console=console)

    item = SampleOutput(name="Alice", age=30)
    out = presenter.present(item, format_mode="table")

    assert out == {"name": "Alice", "age": 30}
    rendered = buf.getvalue()
    assert "SampleOutput" in rendered
    assert "Alice" in rendered
    assert "30" in rendered


def test_rich_terminal_presenter_json(capsys):
    presenter = RichTerminalPresenter()
    item = SampleOutput(name="Bob", age=25)
    out = presenter.present(item, format_mode="json")

    assert out == {"name": "Bob", "age": 25}
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed == {"name": "Bob", "age": 25}


def test_rich_terminal_presenter_plain(capsys):
    presenter = RichTerminalPresenter()
    item = SampleOutput(name="Charlie", age=40)
    out = presenter.present(item, format_mode="plain")

    assert out == {"name": "Charlie", "age": 40}
    captured = capsys.readouterr()
    assert "name\tCharlie" in captured.out
    assert "age\t40" in captured.out


def test_rich_terminal_presenter_error():
    err_buf = StringIO()
    stderr_console = Console(file=err_buf, color_system=None)
    presenter = RichTerminalPresenter(stderr_console=stderr_console)

    presenter.print_error("Invalid token")
    err_out = err_buf.getvalue()
    assert "Error:" in err_out
    assert "Invalid token" in err_out
