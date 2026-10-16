"""Unit and topology tests for the To-Do tutorial Hexaflow DAG."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from hexaflow import Workflow, WorkflowStatus

from tests.e2e.tutorials.workflows.todo_tutorial import (
    create_todo_tutorial_workflow,
)


def test_todo_tutorial_dag_structure(
    simulate_workflow: Callable[[Workflow], Any],
) -> None:
    """Validate To-Do tutorial Hexaflow DAG topology, dependencies, and dry-run simulation.

    Args:
        simulate_workflow: Pytest fixture safely simulating workflow execution.

    Notes/Architectural Intent:
        Fast, hermetic unit-level verification of the To-Do journey DAG structure.
        Ensures all 7 chapters are properly chained and dry-run lambdas execute
        without invoking terminal recording or subshells.
    """
    wf = create_todo_tutorial_workflow()

    workflow_name = wf.name
    assert workflow_name == "todo-tutorial-journey"

    step_count = len(wf._steps)
    assert step_count == 7

    step_names = [s.name for s in wf._steps]
    expected_steps = [
        "step_ch01_scaffolding",
        "step_ch02_sqlite_persistence",
        "step_ch03_jwt_rbac",
        "step_ch04_events_outbox",
        "step_ch05_ai_mcp",
        "step_ch06_observability_devtools",
        "step_ch07_grpc_parity",
    ]
    assert step_names == expected_steps

    step_by_name = {s.name: s for s in wf._steps}
    ch02_deps = step_by_name["step_ch02_sqlite_persistence"].depends_on
    assert ch02_deps == ("step_ch01_scaffolding",)

    ch07_deps = step_by_name["step_ch07_grpc_parity"].depends_on
    assert ch07_deps == ("step_ch06_observability_devtools",)

    # Validate Mermaid visualization generation
    mermaid_diagram = wf.to_mermaid()
    has_mermaid_nodes = (
        "step_ch01_scaffolding" in mermaid_diagram
        and "step_ch07_grpc_parity" in mermaid_diagram
    )
    assert has_mermaid_nodes is True

    # Validate ASCII tree generation
    ascii_tree = wf.to_ascii()
    has_ascii_nodes = (
        "step_ch01_scaffolding" in ascii_tree and "step_ch07_grpc_parity" in ascii_tree
    )
    assert has_ascii_nodes is True

    # Validate dry-run DAG simulation without executing terminal commands
    sim_res = simulate_workflow(wf)
    sim_status = sim_res.status
    assert sim_status == WorkflowStatus.COMPLETED

    is_dry_run = sim_res.is_dry_run
    assert is_dry_run is True

    sim_step_count = len(sim_res.step_checkpoints)
    assert sim_step_count == 7


__all__ = [
    "test_todo_tutorial_dag_structure",
]
