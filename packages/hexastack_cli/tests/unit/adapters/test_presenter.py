import json
import os
from io import StringIO
from unittest.mock import patch

from rich.console import Console

from hexastack_cli.adapters.presenter import RichTerminalPresenter
from hexastack_core.domain import Generic


class SampleOutput(Generic):
    name: str
    age: int


class ListOutput(Generic):
    tags: list[str]


def test_rich_terminal_presenter_error():
    err_buf = StringIO()
    stderr_console = Console(file=err_buf, color_system=None)
    presenter = RichTerminalPresenter(stderr_console=stderr_console)

    presenter.print_error("Invalid token")
    err_out = err_buf.getvalue()
    assert "Error:" in err_out
    assert "Invalid token" in err_out


def test_rich_terminal_presenter_print_exception():
    err_buf = StringIO()
    stderr_console = Console(file=err_buf, color_system=None)
    presenter = RichTerminalPresenter(stderr_console=stderr_console)

    try:
        raise ValueError("Simulated crash")
    except ValueError:
        presenter.print_exception()

    err_out = err_buf.getvalue()
    assert "Simulated crash" in err_out


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


def test_rich_terminal_presenter_non_model_data(capsys):
    buf = StringIO()
    console = Console(file=buf, color_system=None, width=80)
    presenter = RichTerminalPresenter(console=console)

    # 1. Plain string
    presenter._present_plain("single_string")
    captured = capsys.readouterr()
    assert captured.out == "single_string\n"

    # 2. Plain list
    presenter._present_plain(["item_1", "item_2"])
    captured_list = capsys.readouterr()
    assert captured_list.out == "item_1\nitem_2\n"

    # 3. Table list
    presenter._present_table(SampleOutput(name="x", age=1), ["tag1", "tag2"])
    rendered = buf.getvalue()
    assert "tag1" in rendered
    assert "tag2" in rendered


def test_rich_terminal_presenter_no_color():
    with patch.dict(os.environ, {"NO_COLOR": "1"}):
        presenter = RichTerminalPresenter()
        assert presenter._console.no_color is True
