"""End-to-end recording and micro-segment verification for To-Do tutorial journey."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

import pytest
from hexaflow import Workflow, WorkflowStatus

from hexastack_cli.testing.narrator import CliNarrator
from tests.e2e.tutorials.workflows.todo_tutorial import (
    create_todo_tutorial_workflow,
)


@pytest.mark.demo
def test_todo_tutorial_journey(
    cli_narrator_factory: Callable[[str], CliNarrator],
    run_workflow: Callable[[Workflow], Any],
) -> None:
    """Execute complete 7-chapter To-Do tutorial DAG and record micro-segment video clips.

    Args:
        cli_narrator_factory: Pytest fixture factory producing configured CliNarrator instances.
        run_workflow: Pytest fixture executing workflow safely in pytest-asyncio environments.

    Notes/Architectural Intent:
        Executes the atomic 7-chapter DAG with state preservation across all steps.
        When RECORD_DEMO=1 is set, records WebM video clips and WebVTT subtitle files
        to 'docs/assets/demos' for documentation embedding.
    """
    expected_segment_keys = [
        "todo-ch01-cli-demo-part1-scaffolding",
        "todo-ch01-cli-demo-part2-layout",
        "todo-ch02-cli-demo-part1-sqlite",
        "todo-ch02-cli-demo-part2-migrations",
        "todo-ch03-cli-demo",
        "todo-ch04-cli-demo",
        "todo-ch05-cli-demo",
        "todo-ch06-cli-demo",
        "todo-ch07-cli-demo",
    ]

    narrator = cli_narrator_factory("todo")
    wf = create_todo_tutorial_workflow(narrator)

    res = run_workflow(wf)

    res_status = res.status
    assert res_status == WorkflowStatus.COMPLETED

    segment_count = narrator._segment_count
    assert segment_count == 9

    if os.environ.get("RECORD_DEMO") == "1":
        artifacts = narrator.finish()

        for seg_key in expected_segment_keys:
            seg_dict = narrator.segments.get(seg_key)
            has_seg = seg_dict is not None
            assert has_seg is True
            assert seg_dict is not None

            webm_file = seg_dict.get("webm")
            has_webm = webm_file is not None and webm_file.exists()
            assert has_webm is True

            vtt_file = seg_dict.get("vtt")
            has_vtt = vtt_file is not None and vtt_file.exists()
            assert has_vtt is True

            has_webm_artifact = f"{seg_key}_webm" in artifacts
            assert has_webm_artifact is True


__all__ = [
    "test_todo_tutorial_journey",
]
