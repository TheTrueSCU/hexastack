"""Automated USAGE.md generator and verification quality gate for Hexastack packages."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tomllib
from pathlib import Path

from rich.console import Console

from hexastack_tools.utils.help_extractor import (
    extract_command_help,
    extract_subcommands_from_help,
)
from hexastack_tools.utils.workspace import (
    get_repo_root,
    resolve_affected_packages,
)

console = Console()

_TOOLS_SECTION_MAP: dict[str, list[str]] = {
    "🔍 GitHub & PR Examination Tools": [
        "gh-pr-examine",
        "gh-checks",
        "gh-security",
        "gh-code-scanning",
    ],
    "🛡️ Security & Code Quality Gateways": [
        "codeql-scan",
        "check-test-parity",
        "check-all-statements",
        "fix-all-statements",
        "import-linter-run",
        "import-linter-generate",
        "deptry-run",
        "generate-usage-docs",
    ],
    "🧪 Test Execution, Contracts & Mutation": [
        "pytest-run",
        "pytest-archon-generate",
        "inline-snapshot-update",
        "mutmut-run",
        "mutmut-inspect",
    ],
    "📦 Code Architecture & Distribution": [
        "pydeps-generate",
        "pypi-check",
        "pypi-build",
        "pypi-publish",
        "alphabetizer",
        "rope-run",
    ],
}


def build_tools_usage_markdown(root: Path) -> str:
    """Generate canonical USAGE.md for hexastack-tools by introspecting entrypoints."""
    pyproject_path = root / "packages" / "hexastack_tools" / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    scripts: dict[str, str] = data.get("project", {}).get("scripts", {})

    lines: list[str] = [
        "# Hexastack Developer Tools & Usage Guide (`hexastack-tools`)",
        "",
        "> Canonical developer command reference and CLI catalog automatically generated from tool entrypoints.",
        "",
        "---",
        "",
        "## 🏛️ Dogfooding Hexagonal Architecture",
        "",
        "`hexastack-tools` is built strictly according to Hexastack's hexagonal design principles:",
        "- **`domain/`**: Pure data contracts (`PrSummary`, `CheckRunFinding`, `ReviewThread`, `OutputFormat`).",
        "- **`ports/`**: Clean interface contracts (`GitHubApiPort`).",
        "- **`adapters/`**: Pluggable presenters (`rich`, `json`, `plain`) and GitHub API REST/GraphQL clients.",
        "- **`commands/`**: High-performance Typer/Argparse CLI applications with pipe auto-detection.",
        "- **`utils/`**: Shared monorepo workspace discovery and package graph resolvers.",
        "",
        "---",
        "",
        "## ⚙️ Output Presentation Formats",
        "",
        "All inspection commands support `--format / -f`:",
        "- **`auto` (default)**: Automatically outputs interactive ANSI tables/panels when attached to a terminal TTY, and switches to clean, tab-delimited plain text (`TSV`) when standard output is piped into Unix filters (`grep`, `awk`, `cut`, `xargs`, etc.).",
        "- **`rich`**: Interactive Rich tables and color-coded status badges.",
        "- **`json`**: Structured JSON for automation, CI scripts, and AI agents.",
        "- **`plain`**: Machine-readable TSV stream.",
        "",
        "---",
        "",
        "## 🛠️ CLI Commands & Usage Catalog",
        "",
    ]

    documented_cmds: set[str] = set()

    for section_title, cmd_list in _TOOLS_SECTION_MAP.items():
        lines.append(f"### {section_title}\n")
        for cmd in cmd_list:
            if cmd not in scripts:
                continue
            documented_cmds.add(cmd)
            help_text = extract_command_help([cmd])
            lines.append(f"#### `{cmd}`\n")
            lines.append("```text")
            lines.append(help_text)
            lines.append("```\n")

    unmapped = sorted(set(scripts.keys()) - documented_cmds)
    if unmapped:
        lines.append("### 🔧 Additional Workspace Tools\n")
        for cmd in unmapped:
            help_text = extract_command_help([cmd])
            lines.append(f"#### `{cmd}`\n")
            lines.append("```text")
            lines.append(help_text)
            lines.append("```\n")

    return "\n".join(lines).strip() + "\n"


def build_umbrella_usage_markdown(root: Path) -> str:
    """Generate canonical USAGE.md for the umbrella hexastack package and subcommands."""
    main_help = extract_command_help(["hexastack"])
    subcommands = extract_subcommands_from_help(main_help)

    lines: list[str] = [
        "# Hexastack CLI & Framework Usage Guide (`hexastack`)",
        "",
        "> Canonical reference guide and command catalog for the Hexastack Unified Developer CLI.",
        "",
        "---",
        "",
        "## 🚀 Unified Entrypoint (`hexastack`)",
        "",
        "```text",
        main_help,
        "```",
        "",
        "---",
        "",
        "## 🛠️ Subcommand Reference Catalog",
        "",
    ]

    for sub in subcommands:
        sub_help = extract_command_help(["hexastack", sub])
        lines.append(f"### `hexastack {sub}`\n")
        lines.append("```text")
        lines.append(sub_help)
        lines.append("```\n")

    return "\n".join(lines).strip() + "\n"


_TARGET_GENERATORS = {
    "tools": (
        "packages/hexastack_tools/USAGE.md",
        build_tools_usage_markdown,
    ),
    "hexastack": (
        "packages/hexastack/USAGE.md",
        build_umbrella_usage_markdown,
    ),
}


def _get_changed_files_for_git() -> list[str]:
    """Retrieve modified files from git staged/unstaged or HEAD commit."""
    try:
        res = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [line.strip() for line in res.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def resolve_impacted_usage_targets(root: Path) -> list[str]:
    """Resolve targets based on git changes, or all if no changes detected."""
    changed = _get_changed_files_for_git()
    if not changed:
        return list(_TARGET_GENERATORS.keys())

    affected = resolve_affected_packages(changed, root)
    if affected is None:
        return list(_TARGET_GENERATORS.keys())

    targets: list[str] = []
    if "tools" in affected:
        targets.append("tools")
    if "hexastack" in affected or "cli" in affected:
        targets.append("hexastack")

    return targets or list(_TARGET_GENERATORS.keys())


def process_package_usage(
    target_key: str,
    root: Path,
    verify: bool,
    fix: bool,
) -> bool:
    """Process USAGE.md for a given target package. Returns True if in sync / fixed."""
    rel_path, generator_fn = _TARGET_GENERATORS[target_key]
    usage_file = root / rel_path

    new_content = generator_fn(root)

    if verify and not fix:
        if not usage_file.is_file():
            console.print(f"[bold red]❌ {rel_path} does not exist.[/bold red]")
            return False
        current_content = usage_file.read_text(encoding="utf-8")
        if current_content.strip() != new_content.strip():
            console.print(
                f"[bold red]❌ {rel_path} is out of date. Run 'uv run generate-usage-docs --fix' to update.[/bold red]"
            )
            return False
        console.print(f"[bold green]✓ {rel_path} is up to date.[/bold green]")
        return True

    # Fix / generate mode
    usage_file.write_text(new_content, encoding="utf-8")
    console.print(f"[bold green]✓ Updated {rel_path}[/bold green]")
    return True


def main() -> None:
    """CLI entrypoint for generate-usage-docs."""
    parser = argparse.ArgumentParser(
        description="Generate, verify, and fix USAGE.md documentation for Hexastack packages."
    )
    parser.add_argument(
        "-p",
        "--package",
        choices=["tools", "hexastack", "all"],
        default=None,
        help="Target package to process (default: auto-detected based on git changes or all)",
    )
    parser.add_argument(
        "-A",
        "--affected",
        action="store_true",
        help="Detect and process only affected packages with CLI impact.",
    )
    parser.add_argument(
        "--check",
        "--verify",
        dest="verify",
        action="store_true",
        help="Verify whether USAGE.md files match in-memory generation (pre-commit quality gate).",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Re-generate and format USAGE.md files directly on disk.",
    )
    args = parser.parse_args()

    root = get_repo_root()

    if args.package and args.package != "all":
        targets = [args.package]
    elif args.package == "all":
        targets = list(_TARGET_GENERATORS.keys())
    elif args.affected:
        targets = resolve_impacted_usage_targets(root)
    else:
        # Default behavior: if --check without flags, check impacted or all
        targets = (
            resolve_impacted_usage_targets(root)
            if args.verify
            else list(_TARGET_GENERATORS.keys())
        )

    all_ok = True
    for target in targets:
        ok = process_package_usage(
            target_key=target,
            root=root,
            verify=args.verify,
            fix=args.fix or (not args.verify),
        )
        if not ok:
            all_ok = False

    sys.exit(0 if all_ok else 1)


__all__ = [
    "build_tools_usage_markdown",
    "build_umbrella_usage_markdown",
    "main",
    "process_package_usage",
    "resolve_impacted_usage_targets",
]
