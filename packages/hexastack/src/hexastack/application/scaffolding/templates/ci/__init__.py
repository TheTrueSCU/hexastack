"""CI/CD workflow template renderers."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hexastack.application.scaffolding.generator import ScaffoldConfig


def render_github_ci() -> str:
    return """name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  check:
    name: Fast Quality Gate (Lint, Types, Unit Tests)
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Pre-Commit Quality Checks
        run: uv run pre-commit run --all-files

      - name: Unit Tests
        run: uv run pytest tests/unit

  hypothesis:
    name: Property-Based Fuzzing & Invariants
    needs: check
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Hypothesis Fuzzing
        run: uv run pytest tests/hypothesis
"""


def render_github_release(config: ScaffoldConfig) -> str:
    return f"""name: Release & Publish

on:
  push:
    tags:
      - "v*"
  workflow_dispatch:
    inputs:
      version:
        description: "Release version (e.g. 0.1.0)"
        required: false
        default: ""

permissions:
  contents: read

concurrency:
  group: release
  cancel-in-progress: false

jobs:
  release:
    name: Resolve Release Version
    runs-on: ubuntu-latest
    permissions:
      contents: read
    outputs:
      released: ${{{{ steps.resolve.outputs.released }}}}
      version: ${{{{ steps.resolve.outputs.version }}}}
      tag: ${{{{ steps.resolve.outputs.tag }}}}
    steps:
      - name: Resolve Release Version
        id: resolve
        env:
          INPUT_VERSION: ${{{{ inputs.version }}}}
        run: |
          if [ -n "$INPUT_VERSION" ]; then
            echo "released=true" >> "$GITHUB_OUTPUT"
            echo "version=$INPUT_VERSION" >> "$GITHUB_OUTPUT"
            echo "tag=v$INPUT_VERSION" >> "$GITHUB_OUTPUT"
          elif [[ "${{{{ github.ref }}}}" == refs/tags/v* ]]; then
            TAG="${{{{GITHUB_REF#refs/tags/}}}}"
            VERSION="${{{{TAG#v}}}}"
            echo "released=true" >> "$GITHUB_OUTPUT"
            echo "version=$VERSION" >> "$GITHUB_OUTPUT"
            echo "tag=$TAG" >> "$GITHUB_OUTPUT"
          else
            echo "released=false" >> "$GITHUB_OUTPUT"
          fi

  publish:
    name: Build & Publish Package
    needs: release
    if: needs.release.outputs.released == 'true'
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - name: Checkout Tagged Release
        uses: actions/checkout@v4
        with:
          ref: ${{{{ needs.release.outputs.tag }}}}

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"

      - name: Build Distribution Packages
        run: uv build --out-dir dist/

      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: dist/
          skip-existing: true
          password: ${{{{ secrets.PYPI_API_TOKEN }}}}

  sbom:
    name: Generate & Attach SBOM
    needs: [release, publish]
    if: needs.release.outputs.released == 'true'
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Checkout Tagged Release
        uses: actions/checkout@v4
        with:
          ref: ${{{{ needs.release.outputs.tag }}}}

      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Generate SBOM (SPDX JSON)
        uses: anchore/sbom-action@v0
        with:
          path: .
          format: spdx-json
          output-file: {config.name}-${{{{ needs.release.outputs.version }}}}-sbom.spdx.json

      - name: Generate SBOM (CycloneDX JSON)
        uses: anchore/sbom-action@v0
        with:
          path: .
          format: cyclonedx-json
          output-file: {config.name}-${{{{ needs.release.outputs.version }}}}-sbom.cyclonedx.json

      - name: Attach SBOMs to GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          tag_name: ${{{{ needs.release.outputs.tag }}}}
          files: |
            {config.name}-${{{{ needs.release.outputs.version }}}}-sbom.spdx.json
            {config.name}-${{{{ needs.release.outputs.version }}}}-sbom.cyclonedx.json
"""


def render_changelog() -> str:
    return """# CHANGELOG

## v0.1.0 (Initial Release)

### Features
* Initial microservice scaffold generated by Hexastack.
* Hexagonal architecture layout (`domain`, `ports`, `adapters`, `infra`).
* Tiered CI quality gates, property fuzzing, and automated distribution pipeline.
"""
