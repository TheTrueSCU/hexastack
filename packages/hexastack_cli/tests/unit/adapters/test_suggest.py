import re

from typer.testing import CliRunner

from hexastack_cli.adapters.suggest import (
    SuggestCommand,
    SuggestGroup,
    SuggestOptionParser,
    TyperSuggest,
    _extract_option_candidates,
    _substitute_flag_token,
    find_closest_match,
    is_interactive,
)
from hexastack_cli.infra.app import create_cli_app
from hexastack_cli.infra.config import HexastackCliConfig

_ANSI_REGEX = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _strip_ansi(text: str) -> str:
    """Strip ANSI escape and color sequences from string output."""
    return _ANSI_REGEX.sub("", text)


def test_find_closest_match():
    # Direct matching
    match_cmd = find_closest_match("deply", ["deploy", "build", "status"])
    assert match_cmd == "deploy"

    # Flag matching with dashes
    match_flag = find_closest_match("--prt", ["--port", "--host", "--verbose"])
    assert match_flag == "--port"

    # Help flag
    match_help = find_closest_match("--hepl", ["--help", "--version"])
    assert match_help == "--help"

    # No match below cutoff
    no_match = find_closest_match("xyz123", ["deploy", "build"])
    assert no_match is None


def test_substitute_flag_token():
    tokens = ["--verbose", "--prt=8080", "positional", "--prt", "9090"]

    # Inline assignment replacement
    res1 = _substitute_flag_token(tokens, "--prt", "--port")
    assert res1 == ["--verbose", "--port=8080", "positional", "--port", "9090"]

    # Exact token replacement
    res2 = _substitute_flag_token(["--prt"], "--prt", "--port")
    assert res2 == ["--port"]

    # Unrelated tokens unchanged
    res3 = _substitute_flag_token(["--host=localhost"], "--prt", "--port")
    assert res3 == ["--host=localhost"]


def test_is_interactive(monkeypatch):
    # Default non-interactive under test runner
    interactive_default = is_interactive()
    assert interactive_default is False

    # Force via environment variable
    monkeypatch.setenv("HEXASTACK_CLI_INTERACTIVE", "1")
    interactive_env = is_interactive()
    assert interactive_env is True

    # Test with mock context
    class MockCtx:
        meta = {"force_interactive": True}

    interactive_forced = is_interactive(MockCtx())
    assert interactive_forced is True


def test_class_hierarchy():
    import typer.core

    assert issubclass(SuggestCommand, typer.core.TyperCommand)
    assert issubclass(SuggestGroup, typer.core.TyperGroup)
    assert issubclass(SuggestOptionParser, object)


def test_extract_option_candidates():
    import typer.main

    app = TyperSuggest()

    @app.command()
    def sample(port: int = 8080, verbose: bool = False):
        pass

    cmd = typer.main.get_command(app)
    ctx = cmd.make_context("sample", [])
    candidates = _extract_option_candidates(cmd.get_params(ctx))
    assert "--port" in candidates
    assert "--verbose" in candidates
    assert "--help" in candidates


def test_exact_command_execution():
    app = TyperSuggest()

    @app.command("deploy")
    def deploy(port: int = 8080):
        print(f"Deployed on port {port}")

    @app.command("build")
    def build():
        print("Built artifact")

    runner = CliRunner()
    res = runner.invoke(app, ["deploy", "--port", "9000"])
    exit_code = res.exit_code
    stdout = res.stdout
    assert exit_code == 0
    assert "Deployed on port 9000" in stdout


def test_subcommand_typo_non_interactive():
    app = TyperSuggest()

    @app.command("deploy")
    def deploy():
        print("Deploying")

    @app.command("build")
    def build():
        print("Building")

    runner = CliRunner()
    res = runner.invoke(app, ["deply"])
    exit_code = res.exit_code
    output = _strip_ansi(res.output)
    assert exit_code == 2
    assert "Did you mean 'deploy'?" in output


def test_subcommand_typo_interactive_accept():
    app = TyperSuggest()

    @app.command("deploy")
    def deploy():
        print("Deploying successfully")

    @app.command("build")
    def build():
        print("Building")

    runner = CliRunner()
    res = runner.invoke(
        app,
        ["deply"],
        input="y\n",
        env={"HEXASTACK_CLI_INTERACTIVE": "1"},
    )
    exit_code = res.exit_code
    stdout = res.stdout
    assert exit_code == 0
    assert "Deploying successfully" in stdout


def test_subcommand_typo_interactive_decline():
    app = TyperSuggest()

    @app.command("deploy")
    def deploy():
        print("Deploying")

    @app.command("build")
    def build():
        print("Building")

    runner = CliRunner()
    res = runner.invoke(
        app,
        ["deply"],
        input="n\n",
        env={"HEXASTACK_CLI_INTERACTIVE": "1"},
    )
    exit_code = res.exit_code
    assert exit_code == 1


def test_option_typo_non_interactive():
    app = TyperSuggest()

    @app.command()
    def deploy(port: int = 8080):
        print(f"Deployed on {port}")

    runner = CliRunner()
    # Separated option flag
    res1 = runner.invoke(app, ["--prt", "9000"])
    code1 = res1.exit_code
    out1 = _strip_ansi(res1.output)
    assert code1 == 2
    assert "Did you mean '--port'?" in out1

    # Inline '=' assignment
    res2 = runner.invoke(app, ["--prt=9000"])
    code2 = res2.exit_code
    out2 = _strip_ansi(res2.output)
    assert code2 == 2
    assert "Did you mean '--port'?" in out2


def test_option_typo_interactive_accept():
    app = TyperSuggest()

    @app.command()
    def deploy(port: int = 8080):
        print(f"Deployed on {port}")

    runner = CliRunner()
    res = runner.invoke(
        app,
        ["--prt=9090"],
        input="y\n",
        env={"HEXASTACK_CLI_INTERACTIVE": "1"},
    )
    exit_code = res.exit_code
    stdout = res.stdout
    assert exit_code == 0
    assert "Deployed on 9090" in stdout


def test_option_typo_interactive_decline():
    app = TyperSuggest()

    @app.command()
    def deploy(port: int = 8080):
        print(f"Deployed on {port}")

    runner = CliRunner()
    res = runner.invoke(
        app,
        ["--prt=9090"],
        input="n\n",
        env={"HEXASTACK_CLI_INTERACTIVE": "1"},
    )
    exit_code = res.exit_code
    assert exit_code == 1


def test_negative_number_immunity():
    app = TyperSuggest()

    @app.command()
    def compute(val: int, offset: int = 0):
        print(f"Val: {val}, Offset: {offset}")

    runner = CliRunner()
    # Positional negative integer
    res1 = runner.invoke(app, ["-42"])
    code1 = res1.exit_code
    out1 = res1.stdout
    assert code1 == 0
    assert "Val: -42, Offset: 0" in out1

    # Option value negative integer
    res2 = runner.invoke(app, ["10", "--offset", "-5"])
    code2 = res2.exit_code
    out2 = res2.stdout
    assert code2 == 0
    assert "Val: 10, Offset: -5" in out2


def test_bare_double_dash_boundary():
    app = TyperSuggest()

    @app.command()
    def execute(arg: str):
        print(f"Arg: {arg}")

    runner = CliRunner()
    # Double dash prevents --unknown from being parsed as an option
    res = runner.invoke(app, ["--", "--unknown-flag"])
    exit_code = res.exit_code
    stdout = res.stdout
    assert exit_code == 0
    assert "Arg: --unknown-flag" in stdout


def test_unrecognized_without_suggestion():
    app = TyperSuggest()

    @app.command("deploy")
    def deploy():
        pass

    @app.command("build")
    def build():
        pass

    runner = CliRunner()
    # Unrecognized subcommand with no close matches
    res1 = runner.invoke(app, ["zzzzzzzz"])
    code1 = res1.exit_code
    assert code1 == 2

    # Unrecognized option with no close matches
    res2 = runner.invoke(app, ["deploy", "--zzzzzzzz"])
    code2 = res2.exit_code
    assert code2 == 2


def test_create_cli_app_integration():
    cfg = HexastackCliConfig(app_name="hexatest", version="0.9.0")
    app = create_cli_app(config=cfg)

    @app.command("serve")
    def serve(port: int = 8000):
        print(f"Serving on {port}")

    assert isinstance(app, TyperSuggest)

    runner = CliRunner()
    # Test --version callback works
    res_ver = runner.invoke(app, ["--version"])
    code_ver = res_ver.exit_code
    out_ver = res_ver.stdout
    assert code_ver == 0
    assert "hexatest 0.9.0" in out_ver

    # Test subcommand suggestion works on create_cli_app
    res_typo = runner.invoke(app, ["sreve"])
    code_typo = res_typo.exit_code
    out_typo = _strip_ansi(res_typo.output)
    assert code_typo == 2
    assert "Did you mean 'serve'?" in out_typo
