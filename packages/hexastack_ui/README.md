# hexastack-ui

Reactive UI presentation adapters and turnkey DevTools dashboard for Hexastack.

[![PyPI: hexastack-ui](https://img.shields.io/pypi/v/hexastack-ui.svg)](https://pypi.org/project/hexastack-ui/)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Coverage](https://codecov.io/github/TheTrueSCU/hexastack/graph/badge.svg?component=hexastack_ui)](https://codecov.io/github/TheTrueSCU/hexastack)
[![Part of Hexastack](https://img.shields.io/badge/part%20of-hexastack-blueviolet.svg)](https://dopplereffect.us/hexastack/)
[![Governed by Hexaqual](https://img.shields.io/badge/governed%20by-hexaqual-10b981.svg)](https://dopplereffect.us/hexaqual/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](../../LICENSE)

> Part of the [**Hexastack Framework**](https://dopplereffect.us/hexastack/) · Governed by [**Hexaqual**](https://dopplereffect.us/hexaqual/).


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
