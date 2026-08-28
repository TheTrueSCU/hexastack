"""OpenSSF Scorecard and Security Governance template renderers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack.application.scaffolding.generator import ScaffoldConfig


def render_github_scorecard() -> str:
    return """name: OpenSSF Scorecard

on:
  branch_protection_rule:
  schedule:
    - cron: "0 4 * * 1"
  push:
    branches: [main]

permissions: read-all

jobs:
  analysis:
    name: Scorecard Security Analysis
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      id-token: write

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4
        with:
          persist-credentials: false

      - name: Run OpenSSF Scorecard Analysis
        uses: ossf/scorecard-action@v2.4.0
        with:
          results_file: results.sarif
          results_format: sarif
          publish_results: true

      - name: Upload SARIF results to GitHub Security tab
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
"""


def render_security_md(config: ScaffoldConfig) -> str:
    return f"""# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in `{config.name}`, please report it responsibly:

1. **Do not create a public GitHub issue.**
2. Report vulnerabilities via GitHub Security Advisories or by emailing the maintainers.
3. Include detailed steps to reproduce the vulnerability.
4. Maintainers will acknowledge receipt within 48 hours and provide remediation updates.
"""


def render_governance_md(config: ScaffoldConfig) -> str:
    return f"""# Project Governance & Roles

## Overview
`{config.name}` is maintained under a meritocratic governance structure following standard OpenSSF guidelines.

## Roles & Responsibilities
* **Maintainers**: Responsible for reviewing pull requests, cutting releases, and security response.
* **Contributors**: Submit issues, bug fixes, features, and documentation improvements.

## Decision Making
Decisions are reached by consensus on GitHub issues and pull requests. Architectural changes require maintainer approval and passing status checks.
"""


def render_code_of_conduct_md() -> str:
    return """# Contributor Covenant Code of Conduct

## Our Pledge
We as members, contributors, and leaders pledge to make participation in our community a harassment-free experience for everyone, regardless of age, body size, visible or invisible disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, caste, color, religion, or sexual identity and orientation.

## Our Standards
* Demonstrating empathy and kindness toward other people
* Being respectful of differing opinions, viewpoints, and experiences
* Giving and gracefully accepting constructive feedback
* Accepting responsibility and apologizing to those affected by our mistakes

## Enforcement
Instances of abusive, harassing, or otherwise unacceptable behavior may be reported to the project maintainers. All complaints will be reviewed and investigated promptly and fairly.
"""
