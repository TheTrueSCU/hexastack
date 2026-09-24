---
trigger: always_on
description: Mandates synchronized documentation, READMEs, Zensical guides, and diagrams whenever features or packages change.
---

## Documentation & Diagram Synchronization Invariants

Whenever adding, updating, or refactoring framework features, adapters, packages, or extras:

1. **Per-Package `README.md` (`packages/<pkg>/README.md`)**:
   - Must document newly introduced public APIs, functions, classes, and decorators.
   - Must list newly available optional extras (e.g. `[mcp]`) and provide brief, runnable code examples.

2. **Root `README.md` (`README.md`)**:
   - When adding a new package or updating existing package capabilities, ensure the root package matrix and installation guides reflect the change.

3. **Zensical Documentation (`docs/`)**:
   - Update corresponding module guides under `docs/` (e.g. `docs/packages/<pkg>.md`, `docs/features/`).
   - If new concepts or cross-package links are introduced (e.g. `hexastack-ai` + `hexastack-mcp`, or `hexastack-qual`), document the architecture, usage, and design decisions.

4. **Diagrams & Visualizations**:
   - If component relationships or workflows change, update embedded Mermaid diagrams.
   - Ensure architecture diagrams (`docs/assets/pydeps/<pkg>.svg`) are regenerated via `hexaqual sanity -p <pkg> --fix` or pre-commit.
   - Verify that documentation builds cleanly without broken cross-references via `zensical build` (or pre-commit `zensical docs build validation`).
