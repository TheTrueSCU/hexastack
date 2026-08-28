## 🚀 Overview & Context

<!-- Brief 1-2 sentence executive summary of the changes and the architectural motivation -->

---

### 📦 Key Architectural Changes & Deliverables

#### 1. Core Feature / Subsystem Enhancements
- **`<Feature/Component>`**:
  - Description of change, design decisions, and architectural invariants preserved.

#### 2. Tests & Fuzzing Verification
- **`<Test Suites Added/Updated>`**:
  - 1:1 test parity verification and coverage metrics (target: $\ge 90\%$).

#### 3. Security & Governance Compliance
- Addressed CodeQL, OpenSSF Scorecard, and supply-chain requirements.

---

### 🛡️ Quality Verification Checklist

- [ ] `pre-commit run --all-files` passes cleanly across all hooks (Ruff, ty, buf, deptry, import-linter, pip-audit).
- [ ] `uv run check-test-parity` passes 100% cleanly (1:1 source-to-test mirror symmetry & directory `__init__.py`).
- [ ] Unit & integration tests pass with $\ge 90\%$ branch coverage.
- [ ] GitHub Advanced Security (CodeQL) reports 0 new vulnerabilities.
- [ ] All required checks satisfied by `CI Success (All Required Checks)` status gate.

---

### 🔗 Related Issues & Epics

- Closes #
- Related to #
