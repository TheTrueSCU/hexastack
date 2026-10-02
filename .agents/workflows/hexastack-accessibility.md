---
name: hexastack-accessibility
description: Running and triaging WCAG 2.1 AA Playwright axe-core accessibility audits for DevTools and UI views.
---

# Workflow: Hexastack UI Accessibility Audit & Triage

This workflow guides developers and AI agents through verifying and triaging WCAG 2.1 AA accessibility compliance across `hexastack-ui` (NiceGUI DevTools) and `hexastack-fastapi` web views.

## 1. Running the Automated E2E Accessibility Suite

Hexastack executes headless browser scans with `axe-core` via Playwright.

### Run All Accessibility Scans
```bash
uv run pytest tests/e2e/test_ui_accessibility.py --no-cov -v --browser chromium
```

### Run Scans with Live Headed Browser (Debugging)
```bash
uv run pytest tests/e2e/test_ui_accessibility.py --no-cov -v --headed
```

## 2. Triaging Accessibility Violations

When an `axe-core` assertion fails:

1. **Inspect Violation Details**:
   - The test failure outputs the list of violation objects containing:
     - `id`: The axe rule identifier (e.g., `color-contrast`, `button-name`, `landmark-one-main`).
     - `impact`: Severity level (`critical`, `serious`, `moderate`, `minor`).
     - `help`: Human-readable remediation guidance and WCAG success criterion link.
     - `nodes`: Array of failing DOM elements with CSS target selectors and HTML snippets.

2. **Common Remediation Steps**:
   - **`button-name`**: Add `aria-label` or `.tooltip(...)` to icon buttons:
     ```python
     ui.button(icon="refresh").props('aria-label="Refresh telemetry stream"')
     ```
   - **`color-contrast`**: Adjust Tailwind/Quasar color classes or CSS tokens to satisfy 4.5:1 text contrast.
   - **`label`**: Ensure form inputs have associated labels:
     ```python
     ui.input(label="Search Command").props('aria-label="Search Command"')
     ```

## 3. Adding Audits for New UI Panels

When adding a new panel to `hexastack-ui`:

1. Open [`tests/e2e/test_ui_accessibility.py`](file:///home/rjdw/Projects/hexastack/tests/e2e/test_ui_accessibility.py).
2. Add a navigation step using `smart_click(page, page.get_by_text("<Panel Title>"))`.
3. Assert visibility of the panel container.
4. Execute `run_axe_scan(page)` and assert `len(critical_violations) == 0`:
   ```python
   # Audit New Panel Tab
   smart_click(page, page.get_by_text("New Panel"))
   expect(page.get_by_text("New Panel Heading")).to_be_visible()
   violations_new = run_axe_scan(page)
   critical_violations_new = [
       v for v in violations_new if v.get("impact") in ("critical", "serious")
   ]
   assert len(critical_violations_new) == 0, (
       f"Accessibility violations on New Panel tab: {critical_violations_new}"
   )
   ```

## 4. CI/CD Gate Verification

Accessibility is validated in Stage 4 of GitHub Actions CI (`e2e-a11y`). Passing `tests/e2e/test_ui_accessibility.py` locally guarantees clean passage of this gate before push.
