"""Feature demo test recording the hexastack scaffolding CLI experience."""

import os
import tempfile
from pathlib import Path

import pytest
import typer
from hexaqual.adapters.testing.narrator import CliNarrator

from hexastack.adapters.cli.scaffolding.commands import add_scaffold_commands


@pytest.mark.demo
def test_scaffolding_cli_demo():
    """Record interactive CLI demonstration for hexastack new & init."""
    app = typer.Typer(name="hexastack")
    add_scaffold_commands(app)
    repo_root = Path.cwd()

    with tempfile.TemporaryDirectory() as tmpdir:
        orig_cwd = Path.cwd()
        try:
            os.chdir(tmpdir)
            narrator = CliNarrator(
                app,
                output_name="hexastack-scaffolding-cli-demo",
                output_dir=repo_root / "docs" / "assets" / "demos",
            )

            # Step 1: Display help menu
            narrator.step("Exploring Hexastack project scaffolding subcommands")
            res_help = narrator.run_command(["new", "--help"])
            exit_code_help = res_help.exit_code
            assert exit_code_help == 0

            # Step 2: Scaffold a new web-api microservice
            narrator.step("Scaffolding a new REST Web API microservice with SQLite")
            res_new = narrator.run_command(
                ["new", "web-api", "billing-service", "--db", "sqlite"]
            )
            exit_code_new = res_new.exit_code
            assert exit_code_new == 0
            billing_toml_exists = Path(
                tmpdir, "billing-service", "pyproject.toml"
            ).exists()
            assert billing_toml_exists is True

            # Checkpoint Segment 1: REST Web API
            seg_rest = narrator.checkpoint_segment("part1-rest-api")

            # Step 3: Scaffold an event-driven service
            narrator.step("Scaffolding an Event-Driven streaming service with Outbox")
            res_event = narrator.run_command(["new", "event-driven", "order-service"])
            exit_code_event = res_event.exit_code
            assert exit_code_event == 0
            order_toml_exists = Path(tmpdir, "order-service", "pyproject.toml").exists()
            assert order_toml_exists is True

            # Finalize Segment 2: Event-Driven Service
            narrator.step(
                "Microservices successfully scaffolded with full hexagonal architecture"
            )
            seg_events = narrator.checkpoint_segment("part2-event-driven")
            artifacts = narrator.finish()

            segment_count = narrator._segment_count
            assert segment_count == 2

            if os.environ.get("RECORD_DEMO") == "1":
                seg_rest_vtt = seg_rest.get("vtt")
                has_rest_vtt = seg_rest_vtt is not None and seg_rest_vtt.exists()
                assert has_rest_vtt is True

                seg_rest_webm = seg_rest.get("webm")
                has_rest_webm = seg_rest_webm is not None and seg_rest_webm.exists()
                assert has_rest_webm is True

                seg_events_vtt = seg_events.get("vtt")
                has_events_vtt = seg_events_vtt is not None and seg_events_vtt.exists()
                assert has_events_vtt is True

                seg_events_webm = seg_events.get("webm")
                has_events_webm = (
                    seg_events_webm is not None and seg_events_webm.exists()
                )
                assert has_events_webm is True

                has_rest_key = (
                    "hexastack-scaffolding-cli-demo-part1-rest-api_webm" in artifacts
                )
                assert has_rest_key is True

                has_events_key = (
                    "hexastack-scaffolding-cli-demo-part2-event-driven_webm"
                    in artifacts
                )
                assert has_events_key is True
        finally:
            os.chdir(orig_cwd)


@pytest.mark.demo
def test_hexaflow_graph_render_cli_demo():
    """Record interactive CLI demonstration for hexaflow graph render & analysis."""
    from hexaflow.cli.main import app as hexaflow_app

    repo_root = Path.cwd()
    output_dir = repo_root / "docs" / "assets" / "demos"

    with tempfile.TemporaryDirectory() as tmpdir:
        workflow_code = """\"\"\"Sample order checkout saga workflow.\"\"\"
from hexaflow import Workflow

checkout_wf = Workflow("order-checkout")


@checkout_wf.step(name="validate_cart")
def validate_cart():
    return {"valid": True}


@checkout_wf.step(name="reserve_inventory", depends_on=["validate_cart"])
def reserve_inventory():
    return {"reserved": True}


@checkout_wf.step(name="process_payment", depends_on=["reserve_inventory"])
def process_payment():
    return {"paid": True}


@checkout_wf.step(name="dispatch_order", depends_on=["process_payment"])
def dispatch_order():
    return {"dispatched": True}
"""
        wf_file = Path(tmpdir) / "checkout_saga.py"
        wf_file.write_text(workflow_code, encoding="utf-8")

        narrator = CliNarrator(
            hexaflow_app,
            output_name="hexaflow-graph-render-cli",
            output_dir=output_dir,
            bin_name="hexaflow",
        )

        # Step 1: Discover options via --help
        narrator.step("Discovering Hexaflow graph visualization & rendering options")
        res_help = narrator.run_command(["graph", "render", "--help"])
        exit_code_help = res_help.exit_code
        assert exit_code_help == 0

        # Step 2: Render GitHub Actions CI pipeline as ASCII tree with critical path
        narrator.step("Rendering CI pipeline as terminal ASCII tree with critical path")
        res_ascii = narrator.run_command(
            ["graph", "render", ".github/workflows/ci.yml", "-f", "ascii", "-c"]
        )
        exit_code_ascii = res_ascii.exit_code
        assert exit_code_ascii == 0

        # Step 3: Render CI pipeline as Mermaid diagram for GitHub Step Summaries
        narrator.step(
            "Generating Mermaid diagram with critical path styling for CI summary"
        )
        res_mermaid = narrator.run_command(
            ["graph", "render", ".github/workflows/ci.yml", "-f", "mermaid", "-c"]
        )
        exit_code_mermaid = res_mermaid.exit_code
        assert exit_code_mermaid == 0

        # Checkpoint Segment 1: Static CI Pipeline Visualization
        seg_ci = narrator.checkpoint_segment("part1-ci-pipeline")

        # Step 4: Topological graph metrics and critical path analysis
        narrator.step(
            "Analyzing workflow topological graph metrics and critical path length"
        )
        res_info = narrator.run_command(["graph", "info", ".github/workflows/ci.yml"])
        exit_code_info = res_info.exit_code
        assert exit_code_info == 0

        # Step 5: Dry-run simulation and materialized dynamic DAG highlighting
        narrator.step("Simulating dry-run execution and rendering materialized DAG")
        res_sim = narrator.run_command(
            [
                "graph",
                "render",
                f"{wf_file}:checkout_wf",
                "--dry-run",
                "-f",
                "ascii",
                "-c",
            ]
        )
        exit_code_sim = res_sim.exit_code
        assert exit_code_sim == 0

        # Finalize Segment 2: Dynamic Saga Simulation & Analysis
        narrator.step("Hexaflow graph rendering and DAG analysis complete")
        seg_saga = narrator.checkpoint_segment("part2-saga-simulation")
        artifacts = narrator.finish()

        segment_count = narrator._segment_count
        assert segment_count == 2

        if os.environ.get("RECORD_DEMO") == "1":
            seg_ci_vtt = seg_ci.get("vtt")
            has_ci_vtt = seg_ci_vtt is not None and seg_ci_vtt.exists()
            assert has_ci_vtt is True

            seg_ci_webm = seg_ci.get("webm")
            has_ci_webm = seg_ci_webm is not None and seg_ci_webm.exists()
            assert has_ci_webm is True

            seg_saga_vtt = seg_saga.get("vtt")
            has_saga_vtt = seg_saga_vtt is not None and seg_saga_vtt.exists()
            assert has_saga_vtt is True

            seg_saga_webm = seg_saga.get("webm")
            has_saga_webm = seg_saga_webm is not None and seg_saga_webm.exists()
            assert has_saga_webm is True

            has_ci_key = "hexaflow-graph-render-cli-part1-ci-pipeline_webm" in artifacts
            assert has_ci_key is True

            has_saga_key = (
                "hexaflow-graph-render-cli-part2-saga-simulation_webm" in artifacts
            )
            assert has_saga_key is True
