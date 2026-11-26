# hexastack-qual

> 🛡️ **Hexagonal quality, governance, and release adapter integrating hexaqual with CQRS, MCP, UI, and Events.**

Part of the [Hexastack](https://dopplereffect.us/hexastack/) ecosystem.

[![PyPI: hexastack-qual](https://img.shields.io/pypi/v/hexastack-qual.svg)](https://pypi.org/project/hexastack-qual/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://codecov.io/github/TheTrueSCU/hexastack/graph/badge.svg?component=hexastack_qual)](https://codecov.io/github/TheTrueSCU/hexastack)
[![Part of Hexastack](https://img.shields.io/badge/part%20of-hexastack-blueviolet.svg)](https://dopplereffect.us/hexastack/)
[![Governed by Hexaqual](https://img.shields.io/badge/governed%20by-hexaqual-10b981.svg)](https://dopplereffect.us/hexaqual/)
[![Tested on Hexaqueue](https://img.shields.io/badge/tested%20on-hexaqueue-blue.svg)](https://dopplereffect.us/hexaqueue/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](../../LICENSE)

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

# Dispatch queries and commands asynchronously via the CQRS pipeline
scorecard = await pipeline.execute_async(GetQualityScorecardQuery(package="core"))
print(
    f"Healthy: {scorecard.is_healthy}, Violations: {len(scorecard.complexity_violations)}"
)

result = await pipeline.execute_async(RunSanityCheckCommand(package="core", skip_tests=True))
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
