# Feature Demos & Walkthroughs

> Visual, narrated walkthroughs recorded automatically via our test suites using `RECORD_DEMO=1`.

---

## 1. Project Scaffolding CLI Experience

Watch the `hexastack` zero-install CLI in action — generating production microservices with full hexagonal directory layouts, import-linter contracts, and passing test suites.

### Part 1: REST Web API Microservice with SQLite
<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="assets/demos/hexastack-scaffolding-cli-demo-part1-rest-api.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="assets/demos/hexastack-scaffolding-cli-demo-part1-rest-api.vtt" default>
</video>

### Part 2: Event-Driven Streaming Service with Outbox
<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="assets/demos/hexastack-scaffolding-cli-demo-part2-event-driven.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="assets/demos/hexastack-scaffolding-cli-demo-part2-event-driven.vtt" default>
</video>

---

## 2. Interactive DevTools Dashboard (NiceGUI + FastAPI)

Explore the built-in developer console providing live CQRS message dispatching, pipeline inspection, and real-time execution telemetry:

<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="assets/demos/devtools-interactive-ping-dispatcher.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="assets/demos/devtools-interactive-ping-dispatcher.vtt" default>
</video>

---

## 3. Workflow Orchestration & Saga Simulation (Hexaflow + DevTools)

Inspect DAG execution graphs, adjust layout orientations, toggle critical path bottlenecks, and simulate dry-run saga checkpoints fail-closed with zero side-effects:

<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="assets/demos/devtools-workflow-saga-simulator.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="assets/demos/devtools-workflow-saga-simulator.vtt" default>
</video>

---

## 4. Pipeline DAG Analysis & Critical Path CLI (`hexaflow graph render`)

Inspect complex workflows and GitHub Actions CI pipelines directly from your terminal — rendering ASCII dependency trees, detecting critical path bottlenecks, generating Mermaid diagrams for CI summaries, and simulating dry-run saga execution.

### Part 1: CI Pipeline ASCII Tree & Mermaid Diagram Generation
<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="assets/demos/hexaflow-graph-render-cli-part1-ci-pipeline.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="assets/demos/hexaflow-graph-render-cli-part1-ci-pipeline.vtt" default>
</video>

### Part 2: Topological Graph Metrics & Dry-Run Saga Simulation
<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="assets/demos/hexaflow-graph-render-cli-part2-saga-simulation.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="assets/demos/hexaflow-graph-render-cli-part2-saga-simulation.vtt" default>
</video>

---

## 5. Live Resource Interconnect Topology (Hexastack DevTools)

Explore the live architectural interconnect graph rendered directly inside the DevTools console — tracing relationships across entrypoint clients, execution middlewares, CQRS command/query dispatchers, distributed event brokers, and persistence ports:

<video controls autoplay loop muted playsinline width="100%" style="border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.4);">
  <source src="assets/demos/devtools-resource-topology.webm" type="video/webm">
  <track label="English" kind="subtitles" srclang="en" src="assets/demos/devtools-resource-topology.vtt" default>
</video>

---

## In-Depth Articles

!!! tip "On DEV.to"
    [Reactive DevTools in Python with NiceGUI](devto://nicegui-reactive-devtools) —
    how the `hexastack-ui` DevTools console works, what you get out of the box, and how to
    extend or override panels for your own service.
