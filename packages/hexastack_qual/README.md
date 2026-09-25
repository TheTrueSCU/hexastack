# hexastack-qual

> 🛡️ **Hexagonal quality, governance, and release adapter integrating hexaqual with CQRS, MCP, UI, and Events.**

Part of the [Hexastack](https://dopplereffect.us/hexastack/) ecosystem.

---

## 🌟 Overview

`hexastack-qual` bridges [**Hexaqual**](https://github.com/TheTrueSCU/hexaqual) into Hexastack applications:
- **CQRS Execution Pipeline**: Execute sanity checks, statement formatting, and mutant audits via decoupled `Command` and `Query` objects with full OpenTelemetry tracing and structured logging.
- **Model Context Protocol (MCP)**: Expose `@mcp_tool` and `@mcp_resource` endpoints for AI coding assistants (Claude Desktop, Cursor, Antigravity) to audit complexity, test parity, and mutant resilience.
- **DevTools Console Panel**: Mount a reactive NiceGUI dashboard in `/devtools` showing live quality gauges and one-click remediation actions.
- **Distributed Event Publishing**: Emit domain events (`QualityGateFailedEvent`, `CriticalMutantSurvivingEvent`) over `hexastack-events` to Apprise or NATS.

---

## 📦 Installation

```bash
# Core adapter (CQRS pipeline + Hexaqual runner)
pip install hexastack-qual

# With Model Context Protocol (MCP) server support
pip install "hexastack-qual[mcp]"

# With NiceGUI DevTools console tab
pip install "hexastack-qual[ui]"

# With distributed event publishing
pip install "hexastack-qual[events]"

# All extras
pip install "hexastack-qual[all]"
```

---

## 🚀 Quickstart

### 1. CQRS Pipeline Execution

```python
from hexastack_cqrs.infra.pipeline import ExecutionPipeline
from hexastack_qual.adapters.cqrs.commands import RunSanityCheckCommand
from hexastack_qual.adapters.cqrs.queries import GetQualityScorecardQuery

# Dispatch queries and commands via the CQRS pipeline
scorecard = await pipeline.execute(GetQualityScorecardQuery(package="core"))
print(
    f"Healthy: {scorecard.is_healthy}, Violations: {len(scorecard.complexity_violations)}"
)

result = await pipeline.execute(RunSanityCheckCommand(package="core", skip_tests=True))
print(f"Sanity status: {result.success}")
```

### 2. Exposing Quality over MCP

```python
from hexastack_qual.adapters.mcp import get_quality_tools

# Attach quality inspection tools to an AI agent
agent = create_cqrs_agent(
    pipeline=pipeline,
    tools=get_quality_tools(),
    system_prompt="You are an autonomous refactoring agent with self-verification tools.",
)
```

---

## 🏛️ Architecture

```
hexastack_qual/
├── domain/       # Pure models (QualityScorecard, ComplexityMetric), exceptions, and events
├── ports/        # QualityAuditorPort, MutationInspectorPort, PrDiagnosticPort
├── adapters/     # Hexaqual runner, CQRS handlers, MCP tools, NiceGUI panel, Events publisher
└── infra/        # QualBootstrapper (DI container registration) and Typer CLI
```
