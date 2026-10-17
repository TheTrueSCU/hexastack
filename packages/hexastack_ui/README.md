# hexastack-ui

Reactive UI presentation adapters and turnkey DevTools dashboard for Hexastack.

[![PyPI: hexastack-ui](https://img.shields.io/pypi/v/hexastack-ui.svg)](https://pypi.org/project/hexastack-ui/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://codecov.io/github/TheTrueSCU/hexastack/graph/badge.svg?component=hexastack_ui)](https://codecov.io/github/TheTrueSCU/hexastack)
[![Part of Hexastack](https://img.shields.io/badge/part%20of-hexastack-blueviolet.svg)](https://dopplereffect.us/hexastack/)
[![Governed by Hexaqual](https://img.shields.io/badge/governed%20by-hexaqual-10b981.svg)](https://dopplereffect.us/hexaqual/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](../../LICENSE)

[![Accessibility: WCAG 2.1 AA](https://img.shields.io/badge/accessibility-WCAG%202.1%20AA-brightgreen.svg)](https://www.w3.org/WAI/WCAG21/quickref/?levels=aa)
[![Tested with: axe--core](https://img.shields.io/badge/tested%20with-axe--core-4353ff.svg?logo=deque)](https://github.com/dequelabs/axe-core)

> Part of the [**Hexastack Framework**](https://dopplereffect.us/hexastack/) · Governed by [**Hexaqual**](https://dopplereffect.us/hexaqual/).

---

## 1. Overview & Capabilities

`hexastack-ui` provides reactive web and terminal user interface adapters for Hexastack architectures, headlined by the turnkey **Hexastack DevTools Console**:

- **NiceGUI Reactive Web Presentation**: Build domain UI pages with `@ui_page`, mount reactive sub-applications with `mount_ui_app`, and dispatch directly to the CQRS bus using `dispatch_command` and `dispatch_query`.
- **Live CQRS Dispatcher & Explorer**: Test and trigger command handlers and queries directly in your browser with dynamic input forms and schema validation.
- **Resource Interconnect Topology Navigation**: Explore the live architectural interconnect graph, visually tracing links across inbound HTTP endpoints, middlewares, CQRS buses, distributed event brokers, and outbound persistence ports.
- **Hexaflow Workflow Visualizer & Saga Simulator**: Live Mermaid diagram generation for CQRS sagas, TD/LR layout orientation toggling, critical path detection, and dry-run saga simulation with step highlighting.
- **Dynamic Feature Flag Hot-Swapping**: Inspect evaluated feature flags in real time and apply temporary in-memory overrides without rebooting servers or clearing caches.
- **DI Container & Configuration Inspector**: Inspect active service registrations, singletons, scoped instances, and loaded configuration schemas in the `rodi` DI container.
- **Guaranteed WCAG 2.1 AA Accessibility**: Every DevTools panel, modal, and button is tested end-to-end with Playwright and `axe-core`, guaranteeing **zero critical and zero serious** violations.

---

## 2. Package Anatomy

```
hexastack_ui/
├── adapters/
│   ├── nicegui/        # DevTools console, workflow simulator, topology visualizer
│   └── textual/        # Terminal TUI adapters (in development)
├── domain/             # UI models, navigation state, DevTools tabs
├── ports/              # UI presentation interfaces
└── infra/              # UiBootstrapper (order=35), FastAPI mounting adapters
```

---

## 3. Quickstart: Launching the DevTools Console

### Option A: Via the Hexastack CLI
```bash
# Launch DevTools on http://127.0.0.1:8000/_devtools
hexastack ui
```

### Option B: Mount into an Existing FastAPI Application
```python
from fastapi import FastAPI
from hexastack_ui.adapters.nicegui.devtools import mount_devtools_dashboard

app = FastAPI(title="My Hexastack Service")

# Mount interactive DevTools console under /_devtools
mount_devtools_dashboard(app, path="/_devtools")
```

### Option C: Defining Reactive Domain Pages
```python
from nicegui import ui
from hexastack_ui.infra.decorators import ui_page
from hexastack_ui.adapters.nicegui.dispatcher import dispatch_command
from my_domain.commands import CreateOrderCommand


@ui_page("/orders/new")
def new_order_page():
    ui.label("Create New Order").classes("text-2xl font-bold")

    item_input = ui.input("Item Name")
    qty_input = ui.number("Quantity", value=1, min=1)

    async def submit():
        cmd = CreateOrderCommand(item=item_input.value, quantity=int(qty_input.value))
        res = await dispatch_command(cmd)
        ui.notify(f"Order created: {res.order_id}", type="positive")

    ui.button("Submit Order", on_click=submit).props("primary")
```

---

## 4. Installation

```bash
# Standalone install with NiceGUI engine
pip install hexastack-ui[nicegui]

# With all UI extras
pip install hexastack-ui[all]

# Via the umbrella Hexastack framework
pip install hexastack[ui]
```

---

## 5. Accessibility Invariants (a11y)

Hexastack UI enforces strict accessibility standards verified continuously in CI:
- **Zero Critical/Serious Violations**: Validated under `wcag2a`, `wcag2aa`, and `wcag21aa` tags via `axe-core`.
- **4.5:1 Minimum Contrast**: Enforced for all body text, status indicators, and syntax highlights.
- **Accessible Interactive Controls**: Tooltips, aria-labels, and keyboard navigation on all interactive nodes and buttons.
