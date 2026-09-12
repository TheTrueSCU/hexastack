"""CQRS command handlers for architecture and documentation generators.

Notes/Architectural Intent:
    Orchestrates execution of pydeps dependency diagram generation, USAGE.md catalog
    updates, and pytest-archon boundary test scaffolding, returning immutable domain reports.
"""

from __future__ import annotations

import difflib
import subprocess
import tomllib
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from hexastack_tools.domain.generators import (
    ArchonReport,
    GenerateArchonTestsCommand,
    GeneratePydepsCommand,
    GenerateUsageDocsCommand,
    PydepsDiagramResult,
    PydepsReport,
    UsageDocsReport,
)
from hexastack_tools.utils.help_extractor import (
    extract_command_tree_bfs,
    extract_commands_parallel,
    extract_subcommands_from_help,
)
from hexastack_tools.utils.import_linter import get_present_layers
from hexastack_tools.utils.pydeps import (
    generate_overview_diagram,
    generate_package_diagram,
)
from hexastack_tools.utils.workspace import (
    get_package_directories,
    get_package_directory,
    get_repo_root,
    resolve_affected_packages,
)

_TOOLS_SECTION_MAP: dict[str, list[str]] = {
    "🔍 GitHub & PR Examination Tools": [
        "gh-pr-examine",
        "gh-checks",
        "gh-repo",
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
    """Generate canonical USAGE.md for hexastack-tools using parallel command help extraction."""
    pyproject_path = root / "packages" / "hexastack_tools" / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    scripts: dict[str, str] = data.get("project", {}).get("scripts", {})

    all_cmds = [[cmd] for cmd in sorted(scripts.keys())]
    help_map = extract_commands_parallel(all_cmds)

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
            help_text = help_map.get((cmd,), "")
            lines.append(f"#### `{cmd}`\n")
            lines.append("```text")
            lines.append(help_text)
            lines.append("```\n")

    unmapped = sorted(set(scripts.keys()) - documented_cmds)
    if unmapped:
        lines.append("### 🔧 Additional Workspace Tools\n")
        for cmd in unmapped:
            help_text = help_map.get((cmd,), "")
            lines.append(f"#### `{cmd}`\n")
            lines.append("```text")
            lines.append(help_text)
            lines.append("```\n")

    return "\n".join(lines).strip() + "\n"


def build_umbrella_usage_markdown(root: Path) -> str:
    """Generate canonical USAGE.md for the umbrella hexastack package using BFS command tree traversal."""
    tree = extract_command_tree_bfs(["hexastack"])
    main_help = tree.get(("hexastack",), "")
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
        sub_help = tree.get(("hexastack", sub), "")
        lines.append(f"### `hexastack {sub}`\n")
        lines.append("```text")
        lines.append(sub_help)
        lines.append("```\n")

    return "\n".join(lines).strip() + "\n"


_TARGET_GENERATORS: dict[str, tuple[str, Callable[[Path], str]]] = {
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
        # Ignore git diff failure when outside git workspace
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


class GeneratePydepsHandler:
    """Handler executing pydeps architecture dependency diagram generation."""

    def __init__(self, root: Path | None = None, parallel: bool = True) -> None:
        """Initialize GeneratePydepsHandler with workspace root.

        Args:
            root: Root path of monorepo workspace.
            parallel: Whether to execute diagram generation concurrently.
        """
        self._root = root or get_repo_root()
        self._parallel = parallel

    def handle(self, command: GeneratePydepsCommand) -> PydepsReport:
        """Execute pydeps diagram generation across targeted packages.

        Args:
            command: GeneratePydepsCommand specifying target packages.

        Returns:
            PydepsReport with results for each generated SVG.

        Notes/Architectural Intent:
            Concurrently generates individual package dependency diagrams using
            multiprocessing when parallel is True, or sequentially when False.
        """
        if command.packages:
            packages = [get_package_directory(p, self._root) for p in command.packages]
        else:
            packages = get_package_directories(self._root)

        results: list[PydepsDiagramResult] = []
        overview_path = generate_overview_diagram(self._root)
        if overview_path:
            results.append(
                PydepsDiagramResult(
                    name="Monorepo Overview", path=overview_path, success=True
                )
            )

        if not self._parallel:
            for pkg in packages:
                path = generate_package_diagram(pkg, self._root)
                results.append(
                    PydepsDiagramResult(
                        name=pkg.name,
                        path=path or "",
                        success=bool(path),
                    )
                )
        else:
            with ProcessPoolExecutor() as executor:
                futures = {
                    executor.submit(generate_package_diagram, pkg, self._root): pkg.name
                    for pkg in packages
                }
                for future in futures:
                    pkg_name = futures[future]
                    path = future.result()
                    results.append(
                        PydepsDiagramResult(
                            name=pkg_name,
                            path=path or "",
                            success=bool(path),
                        )
                    )

        all_ok = all(r.success for r in results) if results else True
        return PydepsReport(results=tuple(results), is_successful=all_ok)


class GenerateUsageDocsHandler:
    """Handler evaluating or updating USAGE.md catalog files."""

    def __init__(self, root: Path | None = None) -> None:
        """Initialize GenerateUsageDocsHandler with workspace root."""
        self._root = root or get_repo_root()

    def handle(self, command: GenerateUsageDocsCommand) -> UsageDocsReport:
        """Audit or regenerate USAGE.md documentation.

        Args:
            command: GenerateUsageDocsCommand specifying check or fix behavior.

        Returns:
            UsageDocsReport detailing updated, up-to-date, or stale files.

        Notes/Architectural Intent:
            Delegates markdown generation to target builders, producing diffs
            for any file differing from generated output.
        """
        if command.package and command.package != "all":
            targets = [command.package]
        elif command.package == "all":
            targets = list(_TARGET_GENERATORS.keys())
        elif command.affected_only:
            targets = resolve_impacted_usage_targets(self._root)
        else:
            targets = list(_TARGET_GENERATORS.keys())

        up_to_date: list[str] = []
        updated: list[str] = []
        stale: list[str] = []
        diffs: list[tuple[str, str]] = []

        for target_key in targets:
            rel_path, generator_fn = _TARGET_GENERATORS[target_key]
            usage_file = self._root / rel_path
            new_content = generator_fn(self._root)

            if command.check_only and not command.fix:
                if not usage_file.is_file():
                    stale.append(rel_path)
                    diffs.append((rel_path, f"File {rel_path} does not exist."))
                    continue

                current_content = usage_file.read_text(encoding="utf-8")
                if current_content.strip() != new_content.strip():
                    stale.append(rel_path)
                    diff_lines = list(
                        difflib.unified_diff(
                            current_content.splitlines(),
                            new_content.splitlines(),
                            fromfile=f"a/{rel_path}",
                            tofile=f"b/{rel_path}",
                            lineterm="",
                        )
                    )
                    diffs.append((rel_path, "\n".join(diff_lines)))
                else:
                    up_to_date.append(rel_path)
            else:
                usage_file.write_text(new_content, encoding="utf-8")
                updated.append(rel_path)

        is_valid = len(stale) == 0
        return UsageDocsReport(
            up_to_date_files=tuple(up_to_date),
            updated_files=tuple(updated),
            stale_files=tuple(stale),
            diffs=tuple(diffs),
            is_valid=is_valid,
        )


class GenerateArchonTestsHandler:
    """Handler scaffolding pytest-archon hexagonal boundary tests."""

    def __init__(self, root: Path | None = None) -> None:
        """Initialize GenerateArchonTestsHandler with workspace root."""
        self._root = root or get_repo_root()

    def handle(self, command: GenerateArchonTestsCommand) -> ArchonReport:
        """Scaffold pytest-archon boundary tests across packages.

        Args:
            command: GenerateArchonTestsCommand with target packages and force flag.

        Returns:
            ArchonReport with list of generated and skipped test paths.

        Notes/Architectural Intent:
            Checks for standard hexagonal architectural layers (domain, ports, adapters,
            infra) before writing boundary assertions.
        """
        packages = (
            [get_package_directory(p, self._root) for p in command.packages]
            if command.packages
            else get_package_directories(self._root)
        )

        generated: list[str] = []
        skipped: list[str] = []

        for pkg_path in packages:
            pkg_name = pkg_path.name
            if not get_present_layers(pkg_path):
                skipped.append(pkg_name)
                continue

            test_lines = [
                f'"""Hexagonal architecture boundary tests for {pkg_name}."""',
                "",
                "from hexastack_core.testing import assert_clean_architecture",
                "",
                "",
                f"def test_{pkg_name.replace('-', '_')}_clean_architecture():",
                f'    """Assert {pkg_name} strictly complies with Hexagonal layer isolation."""',
                f'    assert_clean_architecture("{pkg_name.replace("-", "_")}")',
                "",
            ]
            arch_dir = pkg_path / "tests" / "architecture"
            arch_dir.mkdir(parents=True, exist_ok=True)
            target_file = arch_dir / "test_hexagonal_boundaries.py"
            if target_file.exists() and not command.force:
                skipped.append(pkg_name)
                continue

            target_file.write_text(
                "\n".join(test_lines).strip() + "\n", encoding="utf-8"
            )
            generated.append(str(target_file.relative_to(self._root)))

        return ArchonReport(
            generated_files=tuple(generated),
            skipped_files=tuple(skipped),
            is_successful=True,
        )


__all__ = [
    "_TARGET_GENERATORS",
    "_TOOLS_SECTION_MAP",
    "build_tools_usage_markdown",
    "build_umbrella_usage_markdown",
    "GenerateArchonTestsHandler",
    "GeneratePydepsHandler",
    "GenerateUsageDocsHandler",
    "resolve_impacted_usage_targets",
]
