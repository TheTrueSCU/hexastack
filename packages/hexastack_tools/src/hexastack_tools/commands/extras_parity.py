"""Optional Extras Parity and Umbrella Forwarding Validator for Hexastack."""

from __future__ import annotations

import argparse
import tomllib
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.table import Table

from hexastack_tools.utils.workspace import get_package_directories, get_repo_root

console = Console()


@dataclass
class ExtraParityViolation:
    """Represents a missing or misconfigured optional dependency forwarding rule.

    Notes/Architectural Intent:
        Captures the originating subpackage and the optional extra that is not
        forwarded or mapped in the umbrella package (`hexastack/pyproject.toml`).
    """

    subpackage: str
    extra_name: str
    dependencies: list[str]
    suggested_fix: str


def audit_extras_parity(repo_root: Path) -> list[ExtraParityViolation]:
    """Audit subpackage optional dependencies against umbrella package extras.

    Args:
        repo_root: Root directory of the repository.

    Returns:
        List of ExtraParityViolation instances found.

    Notes/Architectural Intent:
        Guarantees that every optional feature declared in any subpackage (e.g.
        `hexastack-db[sqlite]`, `hexastack-events[nats]`, `hexastack-otel[otlp]`)
        can be installed through the umbrella `hexastack` package (e.g.
        `hexastack[sqlite]`, `hexastack[nats]`, `hexastack[all]`).
    """
    umbrella_toml = repo_root / "packages" / "hexastack" / "pyproject.toml"
    if not umbrella_toml.is_file():
        return [
            ExtraParityViolation(
                subpackage="hexastack",
                extra_name="<root>",
                dependencies=[],
                suggested_fix="Missing packages/hexastack/pyproject.toml file.",
            )
        ]

    with umbrella_toml.open("rb") as f:
        umbrella_data = tomllib.load(f)

    umbrella_extras = umbrella_data.get("project", {}).get("optional-dependencies", {})

    # Flatten all declared requirements across umbrella extras
    all_umbrella_reqs: set[str] = set()
    for reqs in umbrella_extras.values():
        for req in reqs:
            all_umbrella_reqs.add(req)

    violations: list[ExtraParityViolation] = []

    for pkg_dir in get_package_directories(repo_root):
        if pkg_dir.name in ("hexastack", "hexastack_tools", "hexastack_cli"):
            continue

        pyproject = pkg_dir / "pyproject.toml"
        if not pyproject.is_file():
            continue

        with pyproject.open("rb") as f:
            data = tomllib.load(f)

        pkg_name = data.get("project", {}).get("name", pkg_dir.name)
        pkg_extras = data.get("project", {}).get("optional-dependencies", {})

        for extra_name, reqs in pkg_extras.items():
            if extra_name == "testing":
                # Testing extras are development-only and tested via workspace dev dependencies
                continue

            # Check if this subpackage extra is simply an optional integration of another first-party package
            # e.g., hexastack-auth[fastapi] depends on fastapi, or hexastack-fastapi[auth] depends on hexastack-auth
            # In the umbrella package, installing `auth` or `fastapi` already pulls in both packages.
            first_party_internal = extra_name in ("fastapi", "grpc", "auth") and all(
                r.startswith(("hexastack-", "fastapi", "grpcio")) for r in reqs
            )
            if first_party_internal:
                continue

            expected_forward = f"{pkg_name}[{extra_name}]"

            matching_umbrella_extra = umbrella_extras.get(extra_name, [])
            is_forwarded_directly = any(
                expected_forward == r
                or expected_forward in r
                or any(expected_forward == part.strip() for part in r.split("["))
                for r in matching_umbrella_extra
            )
            is_in_any_umbrella_extra = any(
                expected_forward in r or (extra_name in r and pkg_name in r)
                for r in all_umbrella_reqs
            )

            # Special case for subpackage [all] extra: satisfied if umbrella[all] includes pkg[all] or pkg[all,sentry]
            if extra_name == "all":
                is_satisfied = any(
                    pkg_name in r for r in umbrella_extras.get("all", [])
                )
            else:
                is_satisfied = is_forwarded_directly or is_in_any_umbrella_extra

            if not is_satisfied:
                violations.append(
                    ExtraParityViolation(
                        subpackage=pkg_name,
                        extra_name=extra_name,
                        dependencies=reqs,
                        suggested_fix=(
                            f"Add `{expected_forward}` to `packages/hexastack/pyproject.toml` "
                            f"under `[project.optional-dependencies].{extra_name}` or `all`."
                        ),
                    )
                )

    return violations


def generate_extras_mermaid_diagram(repo_root: Path) -> str:
    """Generate a Mermaid dependency graph of all umbrella and subpackage extras.

    Args:
        repo_root: Root directory of the repository.

    Returns:
        Mermaid diagram markdown string.
    """
    umbrella_toml = repo_root / "packages" / "hexastack" / "pyproject.toml"
    if not umbrella_toml.is_file():
        return ""

    with umbrella_toml.open("rb") as f:
        umbrella_data = tomllib.load(f)

    umbrella_extras = umbrella_data.get("project", {}).get("optional-dependencies", {})

    lines = [
        "```mermaid",
        "graph LR",
        '    subgraph Umbrella ["hexastack (Umbrella Package)"]',
    ]
    for extra in sorted(umbrella_extras.keys()):
        if extra != "testing":
            lines.append(f'        U_{extra}["[{extra}]"]')
    lines.append("    end\n")

    lines.append('    subgraph Subpackages ["Workspace Subpackages"]')
    for pkg_dir in get_package_directories(repo_root):
        if pkg_dir.name in ("hexastack", "hexastack_tools", "hexastack_cli"):
            continue
        pyproject = pkg_dir / "pyproject.toml"
        if not pyproject.is_file():
            continue
        with pyproject.open("rb") as f:
            data = tomllib.load(f)
        pkg_name = data.get("project", {}).get("name", pkg_dir.name)
        clean_id = pkg_name.replace("-", "_")
        lines.append(f'        P_{clean_id}["{pkg_name}"]')
    lines.append("    end\n")

    for extra, reqs in sorted(umbrella_extras.items()):
        if extra == "testing":
            continue
        for req in reqs:
            pkg_base = req.split("[")[0].strip()
            if pkg_base.startswith("hexastack-"):
                target_id = pkg_base.replace("-", "_")
                lines.append(f"    U_{extra} --> P_{target_id}")

    lines.append("```")
    return "\n".join(lines)


def main() -> int:
    """CLI entrypoint for extras parity validator and diagram generator."""
    parser = argparse.ArgumentParser(
        description="Audit optional extras parity across workspace subpackages and umbrella package."
    )
    parser.add_argument(
        "--diagram",
        action="store_true",
        help="Generate and print Mermaid dependency diagram of package extras.",
    )
    args = parser.parse_args()

    repo_root = get_repo_root()

    if args.diagram:
        diagram = generate_extras_mermaid_diagram(repo_root)
        console.print(diagram)
        return 0

    violations = audit_extras_parity(repo_root)

    if not violations:
        console.print(
            "[bold green]✓ All subpackage optional extras are properly forwarded in the umbrella package.[/bold green]"
        )
        return 0

    table = Table(
        title="[bold red]❌ Optional Extras Parity Violations[/bold red]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Subpackage", style="bold cyan", width=22)
    table.add_column("Extra", style="yellow", width=16)
    table.add_column("Dependencies", width=30)
    table.add_column("Suggested Fix", style="green")

    for v in violations:
        table.add_row(
            v.subpackage,
            f"[{v.extra_name}]",
            ", ".join(v.dependencies[:2])
            + (
                f" (+{len(v.dependencies) - 2} more)" if len(v.dependencies) > 2 else ""
            ),
            v.suggested_fix,
        )

    console.print(table)
    console.print(
        f"\n[bold red]Found {len(violations)} subpackage extra(s) missing from umbrella packaging.[/bold red]"
    )
    return 1


__all__ = [
    "ExtraParityViolation",
    "audit_extras_parity",
    "generate_extras_mermaid_diagram",
    "main",
]
