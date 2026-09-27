---
trigger: always_on
description: WCAG 2.1 AA accessibility invariants, axe-core scans, and UI test parity for hexastack-ui and hexastack-fastapi.
---

## Hexastack UI Accessibility (a11y) Invariants

Hexastack enforces strict WCAG 2.1 AA compliance across all DevTools components (`hexastack-ui`) and web presentation templates (`hexastack-fastapi`), validated end-to-end via Playwright and `axe-core`.

### Core Architectural Invariants

1. **Zero Critical/Serious Violations**:
   - All rendered DOM trees in Hexastack DevTools and FastAPI web endpoints must pass `axe-core` audits with 0 `critical` and 0 `serious` violations under the `['wcag2a', 'wcag2aa', 'wcag21aa']` standards tags.

2. **Color Contrast Ratios**:
   - Normal text against background must maintain a contrast ratio of at least **4.5:1** (WCAG AA).
   - Graphical elements, UI component boundaries, and large text must maintain at least **3:1**.

3. **Accessible Interactive Controls**:
   - Icon-only buttons (`ui.button(icon=...)` in NiceGUI) must explicitly declare an `aria-label` attribute or provide a native accessible tooltip (`.tooltip(...)`).
   - All input fields, select boxes, and toggles must have associated semantic labels or `aria-label` descriptions.
   - Interactive elements must be keyboard-focusable and maintain visible focus outlines.

4. **Hierarchical Landmarks & Semantics**:
   - Page structures must follow semantic hierarchy (`main`, `nav`, `header`, `section`).
   - Headings must not skip logical levels (e.g. `h1` followed by `h3`).

5. **E2E Test Parity**:
   - Any new DevTools tab, panel, or modal added to `packages/hexastack_ui` or `packages/hexastack_fastapi` **must** have a corresponding audit step added to [`tests/e2e/test_ui_accessibility.py`](file:///home/rjdw/Projects/hexastack/tests/e2e/test_ui_accessibility.py) using `smart_click` and `run_axe_scan(page)`.
   - Test assertions must remain side-effect free (assign violations to variables first before evaluating length) to prevent CodeQL alerts.
