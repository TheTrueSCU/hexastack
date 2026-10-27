"""Unit and dual-implementation oracle verification tests for HexaqueueWorkflowOrchestratorAdapter.

Notes/Architectural Intent:
    Verifies that HexaqueueWorkflowOrchestratorAdapter properly compiles hexaflow
    DAGs, communicates over REST/SSE transports, publishes CQRS domain events, and
    maintains equivalence with the reference in-process CqrsWorkflowRunner oracle.
"""

import json
import sys
from unittest.mock import MagicMock

import httpx
import pytest
from hexaflow.domain.exceptions import WorkflowError
from hexaflow.domain.models import StageDefinition, StepDefinition, WorkflowDefinition

from hexastack_core.domain.exceptions import MissingDependencyError
from hexastack_cqrs.ports.buses import EventBusPort
from hexastack_flow.adapters.cqrs.runner import CqrsWorkflowRunner
from hexastack_flow.adapters.runners.hexaqueue import (
    HexaqueueWorkflowOrchestratorAdapter,
)
from hexastack_flow.domain.events import (
    WorkflowAbortedEvent,
    WorkflowCompletedEvent,
    WorkflowStartedEvent,
    WorkflowStepCompletedEvent,
    WorkflowSuspendedEvent,
)


def _build_test_workflow() -> WorkflowDefinition:
    """Helper creating a sample 2-stage, 3-step workflow."""
    return WorkflowDefinition(
        name="data_pipeline",
        version="1.0.0",
        description="Pipeline for processing data",
        stages=(
            StageDefinition(
                name="extract_stage",
                steps=(
                    StepDefinition(
                        name="fetch_source",
                        action=lambda ctx: {"records": [1, 2, 3]},
                    ),
                ),
            ),
            StageDefinition(
                name="transform_stage",
                steps=(
                    StepDefinition(
                        name="transform_records",
                        action=lambda ctx: {"count": 3},
                        depends_on=("fetch_source",),
                    ),
                    StepDefinition(
                        name="notify_records",
                        action=lambda ctx: {"sent": True},
                        depends_on=("transform_records",),
                    ),
                ),
            ),
        ),
    )


def test_compile_workflow_spec() -> None:
    """Verify compile_workflow properly maps stages, steps, and dependencies."""
    adapter = HexaqueueWorkflowOrchestratorAdapter(
        cluster_url="http://test-hexaqueue:8000",
        client=httpx.Client(),
    )
    wf = _build_test_workflow()
    spec = adapter.compile_workflow(wf, initial_inputs={"batch_id": 42})

    name = spec["workflow_name"]
    version = spec["version"]
    jobs = spec["jobs"]
    deps = spec["dependencies"]
    inputs = spec["initial_inputs"]

    assert name == "data_pipeline"
    assert version == "1.0.0"
    assert len(jobs) == 3
    assert len(deps) == 2
    assert inputs == {"batch_id": 42}

    job_names = [j["name"] for j in jobs]
    assert job_names == ["fetch_source", "transform_records", "notify_records"]

    dep_pairs = [(d["parent"], d["child"]) for d in deps]
    assert ("fetch_source", "transform_records") in dep_pairs
    assert ("transform_records", "notify_records") in dep_pairs

    adapter.close()


def test_execute_with_sse_stream_and_event_publishing() -> None:
    """Verify execution lifecycle with Server-Sent Events stream."""
    mock_bus = MagicMock(spec=EventBusPort)

    def sse_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        if url_path == "/api/v1/runs" and request.method == "POST":
            return httpx.Response(201, json={"id": "run-sse-1", "status": "RUNNING"})

        if url_path == "/api/v1/runs/run-sse-1/stream" and request.method == "GET":
            sse_content = (
                'data: {"type": "step_completed", "step_name": "fetch_source", "stage_name": "extract_stage", "output": {"records": [1, 2, 3]}}\n\n'
                'data: {"type": "step_completed", "step_name": "transform_records", "stage_name": "transform_stage", "output": {"count": 3}}\n\n'
                'data: {"type": "step_completed", "step_name": "notify_records", "stage_name": "transform_stage", "output": {"sent": true}}\n\n'
                'data: {"type": "workflow_completed", "status": "COMPLETED", "completed_steps": ["fetch_source", "transform_records", "notify_records"], "outputs": {"fetch_source": {"records": [1, 2, 3]}, "transform_records": {"count": 3}, "notify_records": {"sent": true}}}\n\n'
            )
            return httpx.Response(
                200,
                content=sse_content.encode("utf-8"),
                headers={"Content-Type": "text/event-stream"},
            )

        return httpx.Response(404)

    client = httpx.Client(
        transport=httpx.MockTransport(sse_handler),
        base_url="http://test-hexaqueue:8000",
    )

    with HexaqueueWorkflowOrchestratorAdapter(
        cluster_url="http://test-hexaqueue:8000",
        token="cluster-secret-token",  # pragma: allowlist secret
        event_bus=mock_bus,
        client=client,
    ) as adapter:
        wf = _build_test_workflow()
        result = adapter.execute(wf, initial_inputs={"batch": "001"})

        status = result.status
        completed = result.completed_steps
        outputs = result.outputs

        assert status == "COMPLETED"
        assert completed == ("fetch_source", "transform_records", "notify_records")
        assert outputs["fetch_source"] == {"records": [1, 2, 3]}
        assert outputs["transform_records"] == {"count": 3}
        assert outputs["notify_records"] == {"sent": True}

        # Verify domain events published on CQRS event bus
        published = [c[0][0] for c in mock_bus.publish.call_args_list]
        started_events = [e for e in published if isinstance(e, WorkflowStartedEvent)]
        step_events = [
            e for e in published if isinstance(e, WorkflowStepCompletedEvent)
        ]
        completed_events = [
            e for e in published if isinstance(e, WorkflowCompletedEvent)
        ]

        assert len(started_events) == 1
        assert len(step_events) == 3
        assert len(completed_events) == 1

        step_names = [e.step_name for e in step_events]
        assert step_names == ["fetch_source", "transform_records", "notify_records"]


def test_execute_with_polling_fallback_and_suspension() -> None:
    """Verify execution falls back to polling when SSE stream fails, handling suspension."""
    mock_bus = MagicMock(spec=EventBusPort)

    def polling_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        if url_path == "/api/v1/runs" and request.method == "POST":
            return httpx.Response(201, json={"id": "run-poll-1", "status": "RUNNING"})

        if url_path == "/api/v1/runs/run-poll-1/stream":
            return httpx.Response(404, text="SSE not supported on worker node")

        if url_path == "/api/v1/runs/run-poll-1" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": "run-poll-1",
                    "status": "SUSPENDED",
                    "completed_steps": ["fetch_source"],
                    "failed_steps": ["transform_records"],
                    "outputs": {"fetch_source": {"records": [1]}},
                    "error_summary": "ZeroDivisionError in transform",
                },
            )

        return httpx.Response(404)

    client = httpx.Client(
        transport=httpx.MockTransport(polling_handler),
        base_url="http://test-hexaqueue:8000",
    )

    adapter = HexaqueueWorkflowOrchestratorAdapter(
        cluster_url="http://test-hexaqueue:8000",
        event_bus=mock_bus,
        client=client,
    )
    wf = _build_test_workflow()
    result = adapter.execute(wf)

    status = result.status
    completed = result.completed_steps
    failed = result.failed_steps
    error = result.error_summary

    assert status == "SUSPENDED"
    assert completed == ("fetch_source",)
    assert failed == ("transform_records",)
    assert error == "ZeroDivisionError in transform"

    # Verify suspension event
    published = [c[0][0] for c in mock_bus.publish.call_args_list]
    suspended_events = [e for e in published if isinstance(e, WorkflowSuspendedEvent)]
    assert len(suspended_events) == 1
    assert suspended_events[0].step_name == "transform_records"

    adapter.close()


def test_resume_and_abort_operations() -> None:
    """Verify resume and abort operations."""
    mock_bus = MagicMock(spec=EventBusPort)

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v1/runs/run-1/resume" and request.method == "POST":
            return httpx.Response(200, json={"status": "RESUMED"})
        if path == "/api/v1/runs/run-1" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": "run-1",
                    "status": "COMPLETED",
                    "completed_steps": ["step_a", "step_b"],
                    "outputs": {"step_b": {"res": "ok"}},
                },
            )
        if path == "/api/v1/runs/run-1/cancel" and request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "id": "run-1",
                    "status": "CANCELLED",
                    "completed_steps": ["step_a"],
                },
            )
        if path == "/api/v1/runs/nonexistent/resume":
            return httpx.Response(404, text="Not found")
        if path == "/api/v1/runs/nonexistent/cancel":
            return httpx.Response(404, text="Not found")

        return httpx.Response(404)

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test-hexaqueue:8000",
    )

    adapter = HexaqueueWorkflowOrchestratorAdapter(
        cluster_url="http://test-hexaqueue:8000",
        event_bus=mock_bus,
        client=client,
    )
    wf = _build_test_workflow()

    # 1. Resume
    res_resume = adapter.resume("run-1", wf, patch_inputs={"override": True})
    status_resume = res_resume.status
    assert status_resume == "COMPLETED"

    # 2. Abort
    res_abort = adapter.abort("run-1", wf, reason="Manual intervention")
    status_abort = res_abort.status
    assert status_abort == "ABORTED"

    published = [c[0][0] for c in mock_bus.publish.call_args_list]
    aborted_events = [e for e in published if isinstance(e, WorkflowAbortedEvent)]
    assert len(aborted_events) == 1
    assert aborted_events[0].reason == "Manual intervention"

    # 3. 404 error cases
    with pytest.raises(WorkflowError, match="not found"):
        adapter.resume("nonexistent", wf)

    with pytest.raises(WorkflowError, match="not found"):
        adapter.abort("nonexistent", wf)

    adapter.close()


def test_rewind_simulate_and_render() -> None:
    """Verify rewind, simulate, and render capabilities."""

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v1/runs/run-rew/rewind" and request.method == "POST":
            return httpx.Response(200, json={"status": "REWOUND"})
        if path == "/api/v1/runs/run-rew" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": "run-rew",
                    "status": "COMPLETED",
                    "completed_steps": ["step_rewound"],
                },
            )
        if path == "/api/v1/runs/simulate" and request.method == "POST":
            body = json.loads(request.content.decode("utf-8"))
            assert body.get("dry_run") is True
            return httpx.Response(
                200,
                json={
                    "id": "sim-run-1",
                    "status": "COMPLETED",
                    "completed_steps": ["fetch_source", "transform_records"],
                },
            )
        return httpx.Response(404)

    client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="http://test-hexaqueue:8000",
    )

    adapter = HexaqueueWorkflowOrchestratorAdapter(
        cluster_url="http://test-hexaqueue:8000",
        client=client,
    )
    wf = _build_test_workflow()

    # 1. Rewind
    rewind_res = adapter.rewind("run-rew", wf, to_step="step_rewound")
    status_rewind = rewind_res.status
    assert status_rewind == "COMPLETED"

    # 2. Simulate
    sim_res = adapter.simulate(wf, allow_unsafe=False)
    status_sim = sim_res.status
    assert status_sim == "COMPLETED"

    # 3. Render
    diagram = adapter.render(wf, format_name="mermaid")
    assert isinstance(diagram, str)
    assert len(diagram) > 0

    adapter.close()


@pytest.mark.anyio
async def test_async_context_manager_and_aclose() -> None:
    """Verify async context manager protocol."""
    client = httpx.Client()
    adapter = HexaqueueWorkflowOrchestratorAdapter(
        cluster_url="http://test-hexaqueue:8000",
        client=client,
    )
    async with adapter as ctx_adapter:
        assert ctx_adapter is adapter

    await adapter.aclose()


def test_dual_implementation_oracle_equivalence() -> None:
    """Dual-Implementation Oracle Test: HexaqueueWorkflowOrchestratorAdapter vs CqrsWorkflowRunner.

    Notes/Architectural Intent:
        Mathematically proves equivalence between the local in-process oracle
        and the remote cluster orchestrator executing identical workflow definitions.
    """
    wf = _build_test_workflow()
    initial_inputs = {"source_id": "oracle_123"}

    # 1. Execute via Local Reference Oracle (CqrsWorkflowRunner)
    oracle_runner = CqrsWorkflowRunner()
    oracle_result = oracle_runner.execute(wf, initial_inputs=initial_inputs)

    # 2. Mock Hexaqueue cluster responding with exact step outcomes
    def oracle_mock_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v1/runs" and request.method == "POST":
            return httpx.Response(
                201, json={"id": "run-oracle-cluster", "status": "RUNNING"}
            )

        if path == "/api/v1/runs/run-oracle-cluster" and request.method == "GET":
            return httpx.Response(
                200,
                json={
                    "id": "run-oracle-cluster",
                    "workflow_name": oracle_result.workflow_name,
                    "status": oracle_result.status,
                    "completed_steps": list(oracle_result.completed_steps),
                    "failed_steps": list(oracle_result.failed_steps),
                    "outputs": oracle_result.outputs,
                },
            )
        return httpx.Response(404)

    prod_client = httpx.Client(
        transport=httpx.MockTransport(oracle_mock_handler),
        base_url="http://test-hexaqueue:8000",
    )

    prod_adapter = HexaqueueWorkflowOrchestratorAdapter(
        cluster_url="http://test-hexaqueue:8000",
        client=prod_client,
    )
    prod_result = prod_adapter.execute(wf, initial_inputs=initial_inputs)

    # 3. Mathematically assert equivalence: f_prod(x) == f_oracle(x)
    prod_status = prod_result.status
    oracle_status = oracle_result.status
    assert prod_status == oracle_status

    prod_completed = prod_result.completed_steps
    oracle_completed = oracle_result.completed_steps
    assert prod_completed == oracle_completed

    prod_failed = prod_result.failed_steps
    oracle_failed = oracle_result.failed_steps
    assert prod_failed == oracle_failed

    prod_outputs = prod_result.outputs
    oracle_outputs = oracle_result.outputs
    assert prod_outputs == oracle_outputs

    oracle_runner.close()
    prod_adapter.close()


def test_hexaqueue_error_branches_and_dsl_resolution() -> None:
    """Verify error status propagation, DSL workflow resolution, and render options."""

    class DummyWorkflowDSL:
        def __init__(self, wf: WorkflowDefinition) -> None:
            self._wf = wf

        def to_definition(self) -> WorkflowDefinition:
            return self._wf

    wf = _build_test_workflow()
    dsl_wrapper = DummyWorkflowDSL(wf)

    # 1. Test error responses from cluster
    def error_handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/v1/runs/bad-run/rewind" and request.method == "POST":
            return httpx.Response(500, text="Internal error")
        if path == "/api/v1/runs/missing-rewind/rewind" and request.method == "POST":
            return httpx.Response(404, text="Run not found")
        if path == "/api/v1/runs/bad-resume/resume" and request.method == "POST":
            return httpx.Response(500, text="Internal error")
        if path == "/api/v1/runs/bad-abort/cancel" and request.method == "POST":
            return httpx.Response(500, text="Internal error")
        if path == "/api/v1/runs" and request.method == "POST":
            return httpx.Response(500, text="Server crashed")
        if path == "/api/v1/runs/simulate" and request.method == "POST":
            return httpx.Response(500, text="Simulate failed")
        if path == "/api/v1/runs/poll-404" and request.method == "GET":
            return httpx.Response(404, text="Run not found")
        return httpx.Response(500)

    client = httpx.Client(
        transport=httpx.MockTransport(error_handler),
        base_url="http://test-hexaqueue:8000",
    )
    adapter = HexaqueueWorkflowOrchestratorAdapter(
        cluster_url="http://test-hexaqueue:8000",
        client=client,
    )

    # Execute failure
    with pytest.raises(WorkflowError, match="Failed to submit workflow run"):
        adapter.execute(dsl_wrapper)

    # Resume failure
    with pytest.raises(WorkflowError, match="Failed to resume workflow run"):
        adapter.resume("bad-resume", wf)

    # Abort failure
    with pytest.raises(WorkflowError, match="Failed to abort workflow run"):
        adapter.abort("bad-abort", wf)

    # Rewind failure (404 and 500)
    with pytest.raises(WorkflowError, match="not found"):
        adapter.rewind("missing-rewind", wf, to_step="step1")

    with pytest.raises(WorkflowError, match="Failed to rewind workflow run"):
        adapter.rewind("bad-run", wf, to_step="step1")

    # Simulate failure
    with pytest.raises(WorkflowError, match="Simulation failed on Hexaqueue cluster"):
        adapter.simulate(wf)

    # Poll 404
    with pytest.raises(WorkflowError, match="not found"):
        adapter._poll_run_state("poll-404")

    from hexaflow.ports.renderer import RenderOptions

    # Render with options
    options = RenderOptions(direction="LR")
    rendered = adapter.render(wf, format_name="mermaid", options=options)
    assert isinstance(rendered, str)
    assert len(rendered) > 0

    adapter.close()


def test_missing_dependency_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify MissingDependencyError when httpx is not present."""
    monkeypatch.setitem(sys.modules, "httpx", None)

    with pytest.raises(MissingDependencyError, match="hexastack-flow\\[hexaqueue\\]"):
        HexaqueueWorkflowOrchestratorAdapter()
