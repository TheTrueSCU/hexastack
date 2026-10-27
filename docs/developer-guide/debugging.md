# Developer Debugging & Algorithmic Tracing

> High-signal, zero-overhead diagnostic tools for inspecting execution flow, variable evolution, and exception frames in Hexastack applications.

---

## 1. Algorithmic Tracing with `snoop`

Complex graph traversal (workflow DAG engines in `hexastack-flow`), hierarchical queue fair-share scheduling (in `hexaqueue`), and state machine transitions often require granular line-by-line inspection of local variable evolution.

Hexastack integrates **`snoop`** via [`hexastack_core.utils.debug.snoop_tracer`](file:///home/rjdw/Projects/hexastack/packages/hexastack_core/src/hexastack_core/utils/debug.py) to provide instant execution tracing with zero production overhead:

### Function Decorator Usage

```python
from hexastack_core.utils.debug import snoop_tracer

# Bare decorator
@snoop_tracer
def resolve_critical_path(dag_nodes: list[dict]) -> list[str]:
    sorted_order = []
    for node in dag_nodes:
        # Snoop automatically logs variable mutations and lines executed
        sorted_order.append(node["id"])
    return sorted_order

# Parameterized decorator with watch expressions
@snoop_tracer(depth=2, watch=("node['id']", "len(sorted_order)"))
def calculate_topological_ranks(dag: dict) -> dict:
    ...
```

### Context Manager Usage

```python
from hexastack_core.utils.debug import snoop_tracer

def process_batch(items: list[int]) -> int:
    preliminary_sum = 0

    # Trace only the critical calculation loop
    with snoop_tracer():
        for item in items:
            preliminary_sum += item * 2

    return preliminary_sum
```

### Production Invariant: Zero-Overhead Degradation

If the `hexastack-core[debug]` extra is not installed, or when running in production:
- [`is_snoop_available()`](file:///home/rjdw/Projects/hexastack/packages/hexastack_core/src/hexastack_core/utils/debug.py#L42) safely returns `False`.
- `snoop_tracer` immediately degrades to a no-op decorator and context manager without invoking bytecode instrumentation or runtime overhead.

---

## 2. Frame-Level Variable Diagnostics with `stackprinter`

Standard Python exception tracebacks only display file paths, line numbers, and error messages. Diagnosing unhandled failures in background tasks or distributed workers requires inspecting variable values at the point of failure.

Hexastack provides [`DiagnosticExceptionFormatter`](file:///home/rjdw/Projects/hexastack/packages/hexastack_logging/src/hexastack_logging/infra/formatters/diagnostics.py) and [`format_diagnostics`](file:///home/rjdw/Projects/hexastack/packages/hexastack_logging/src/hexastack_logging/infra/formatters/diagnostics.py) powered by `stackprinter`:

```python
from hexastack_logging.infra.formatters import format_diagnostics

try:
    execute_workflow_step(step_id, payload)
except Exception as err:
    # Emits formatted traceback with annotated frame variables and redacted secrets
    diagnostic_trace = format_diagnostics(err, style="plaintext")
    logger.error("Step execution failed:\n%s", diagnostic_trace)
```

### Automatic Secret Masking & PII Scrubbing

The diagnostic formatter automatically redacts sensitive variables:
1. **Frame-Level Suppression**: Variable names matching common credential patterns (`token`, `password`, `secret`, `api_key`, `authorization`) have their values replaced with `*****`.
2. **Inline Scrubbing**: Output is piped through `LogSanitizer` to mask Bearer tokens, API credentials, and credit card numbers appearing inline within strings.
