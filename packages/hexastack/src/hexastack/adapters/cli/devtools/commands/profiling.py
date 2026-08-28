"""CLI command definitions for demo showcase and diagnostics.

Notes/Architectural Intent:
    Provides subcommands for inspecting registries, running diagnostic queries,
    and launching interactive developer servers.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import typer

from hexastack_core.domain.exceptions import MissingDependencyError

__all__ = [
    "add_load_command",
    "add_profile_command",
]


def add_profile_command(app: typer.Typer) -> None:
    """Register 'profile' CLI command to capture CPU or Memory flamegraphs with py-spy and memray."""
    profile_app = typer.Typer(
        name="profile",
        help="Profile CPU performance or memory allocations with interactive flamegraphs.",
        no_args_is_help=True,
    )
    app.add_typer(profile_app, name="profile")

    @profile_app.command(
        name="cpu",
        help="Capture CPU flamegraph with py-spy (attach to PID or wrap server command).",
    )
    def profile_cpu(
        pid: int | None = typer.Option(
            None, "--pid", "-p", help="Target process ID to attach to."
        ),
        duration: int = typer.Option(
            15, "--duration", "-d", help="Profiling duration in seconds."
        ),
        output: str = typer.Option(
            "cpu_flamegraph.svg",
            "--output",
            "-o",
            help="Output SVG flamegraph filepath.",
        ),
        rate: int = typer.Option(100, "--rate", "-r", help="Samples per second."),
    ) -> None:
        if importlib.util.find_spec("py_spy") is None:
            raise MissingDependencyError(
                "py-spy is required for CPU profiling. Install with 'uv add --dev py-spy'."
            )
        import subprocess

        if pid is None:
            typer.echo(
                "⚠️ No PID provided. Launch your service with 'hexastack dev', find the PID, and pass '--pid <PID>'."
            )
            raise typer.Exit(code=1)

        typer.echo(
            f"🔥 Profiling CPU on PID {pid} for {duration}s @ {rate}Hz -> {output}..."
        )
        cmd = [
            "py-spy",
            "record",
            "-p",
            str(pid),
            "-d",
            str(duration),
            "-r",
            str(rate),
            "-o",
            output,
        ]
        res = subprocess.run(cmd, check=False)
        if res.returncode == 0:
            typer.echo(f"✅ CPU flamegraph saved to: {Path(output).resolve()}")
        else:
            typer.echo(
                "❌ py-spy failed. You may need 'sudo' on Linux to attach to processes."
            )

    @profile_app.command(
        name="memory",
        help="Generate memory allocation flamegraph using memray.",
    )
    def profile_memory(
        bin_file: str = typer.Option(
            "mem_profile.bin",
            "--bin",
            "-b",
            help="Intermediate binary memory capture file.",
        ),
        output: str = typer.Option(
            "mem_flamegraph.html",
            "--output",
            "-o",
            help="Output HTML flamegraph filepath.",
        ),
    ) -> None:
        if importlib.util.find_spec("memray") is None:
            raise MissingDependencyError(
                "memray is required for Memory profiling. Install with 'uv add --dev memray'."
            )
        import subprocess

        if not Path(bin_file).exists():
            typer.echo(
                f"ℹ️ Target capture file '{bin_file}' not found.\n"
                f"Run your application under memray first:\n"
                f"  uv run memray run -o {bin_file} -m hexastack dev\n"
            )
            raise typer.Exit(code=1)

        typer.echo(f"🧠 Rendering memory flamegraph from {bin_file} -> {output}...")
        cmd = ["memray", "flamegraph", bin_file, "-o", output]
        res = subprocess.run(cmd, check=False)
        if res.returncode == 0:
            typer.echo(f"✅ Memory flamegraph saved to: {Path(output).resolve()}")
        else:
            typer.echo("❌ memray flamegraph rendering failed.")


def add_load_command(app: typer.Typer) -> None:
    """Register 'load' CLI command to execute stress tests via Locust."""

    @app.command(
        name="load",
        help="Execute concurrent load/stress testing scenario using Locust.",
    )
    def load_command(
        host: str = typer.Option(
            "http://127.0.0.1:8000", "--host", "-h", help="Target service host URL."
        ),
        users: int = typer.Option(
            50, "--users", "-u", help="Peak number of concurrent virtual users."
        ),
        spawn_rate: int = typer.Option(
            10, "--spawn-rate", "-r", help="Rate to spawn users per second."
        ),
        run_time: str = typer.Option(
            "15s", "--run-time", "-t", help="Total benchmark run time (e.g. 15s, 1m)."
        ),
        locustfile: str = typer.Option(
            "locustfile.py", "--locustfile", "-f", help="Locustfile scenario filepath."
        ),
        headless: bool = typer.Option(
            True, "--headless/--web", help="Run headlessly in CLI without Web UI."
        ),
    ) -> None:
        if importlib.util.find_spec("locust") is None:
            raise MissingDependencyError(
                "locust is required for load testing. Install with 'uv add --dev locust'."
            )
        import subprocess

        # If default locustfile doesn't exist, create a default in-memory benchmark scenario
        target_locust_path = Path(locustfile)
        if not target_locust_path.exists() and locustfile == "locustfile.py":
            default_content = '''"""Automated default Locust scenario for Hexastack microservices."""

from locust import HttpUser, between, task


class HexastackUser(HttpUser):
    wait_time = between(0.01, 0.05)

    @task(3)
    def get_health(self):
        self.client.get("/health")

    @task(2)
    def get_info(self):
        self.client.get("/info")
'''
            target_locust_path.write_text(default_content, encoding="utf-8")
            typer.echo(f"📝 Generated default '{locustfile}' scenario.")

        typer.echo(
            f"🦗 Launching Locust: {users} users @ {spawn_rate}/s for {run_time} against {host}..."
        )

        cmd = [
            "locust",
            "-f",
            locustfile,
            "--host",
            host,
        ]
        if headless:
            cmd.extend(
                [
                    "--headless",
                    "-u",
                    str(users),
                    "-r",
                    str(spawn_rate),
                    "--run-time",
                    run_time,
                    "--exit-code-on-error",
                    "1",
                ]
            )

        res = subprocess.run(cmd, check=False)
        if res.returncode == 0:
            typer.echo("✅ Load benchmark completed successfully.")
        else:
            typer.echo("⚠️ Load benchmark exited with errors.")
            raise typer.Exit(code=res.returncode)
