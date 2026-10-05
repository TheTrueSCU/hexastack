# Project Governance & Maintainership Model

## 1. Overview
Hexastack is an open-source framework built on strict Hexagonal Architecture principles. This document outlines project governance, maintainer roles, decision-making, and succession planning.

---

## 2. Maintainer Roles & Responsibilities

### Project Lead / Maintainers
- **Repository Administration**: Manage branch protections, repository settings, and CI/CD pipelines.
- **Release Management**: Authorize semantic version releases, review changelogs, and maintain Trusted Publishing on PyPI.
- **Architecture Integrity**: Review pull requests for compliance with hexagonal boundary rules (`import-linter`) and testing rigor standards.
- **Security Triage**: Investigate and address vulnerability reports submitted via GitHub Private Vulnerability Reporting within our SLA (48-hour initial response).

### Active Contributors & Reviewers
- Submit focused pull requests with test parity and type annotations.
- Participate in design reviews, RFC discussions, and community feedback.

---

## 3. Decision-Making & RFC Process
- **Minor Changes & Bug Fixes**: Fast-tracked via pull requests requiring 1 maintainer approval and passing CI gates.
- **Architectural & Breaking Changes**: Documented in an RFC (Issue or Discussion) detailing:
  1. Motivation and problem statement
  2. Hexagonal boundary implications (Domain, Ports, Adapters)
  3. Protobuf / wire format backward compatibility
  4. Migration path for existing consumers

---

## 4. Access Continuity & Succession Planning
To prevent single-point-of-failure risks and ensure long-term maintenance:
- All core credentials (PyPI Trusted Publishing, GitHub Pages, Domain DNS) are bound to organizational identities rather than individual accounts.
- If a primary maintainer becomes inactive for more than 6 months, designated co-maintainers obtain full triage and release administration authority.
