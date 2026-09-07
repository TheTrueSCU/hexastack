# hexastack-ui

Reactive UI presentation adapters and turnkey DevTools dashboard for Hexastack.

## Overview

`hexastack-ui` provides reactive UI integration for Hexastack architectures:
- **NiceGUI Web Adapter**: `@ui_page`, `mount_ui_app`, `dispatch_command`, `dispatch_query`.
- **Interactive DevTools Console**: `mount_devtools_dashboard` inspecting CQRS registries, feature flags, and DI containers.
- **Pluggable Architecture**: Modular ports for expanding to Textual (TUI) and other frontend engines.

## Installation

```bash
# With NiceGUI web engine
pip install hexastack-ui[nicegui]

# Or via the umbrella Hexastack distribution
pip install hexastack[ui]
```
