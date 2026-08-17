"""Shared utilities for architecture test and linter generators."""

from pathlib import Path

PACKAGES_DIR = Path("packages")

HEX_LAYERS = ["domain", "ports", "adapters", "infra", "utils", "testing"]

# Prohibited imports per layer: { layer: [layers it MUST NOT import from] }
LAYER_RESTRICTIONS = {
    # Domain is the pure core
    "domain": ["ports", "adapters", "infra", "testing"],
    # Ports define interfaces; independent of concrete implementations
    "ports": ["adapters", "infra", "testing"],
    # Adapters implement ports/domain; decoupled from test helpers
    "adapters": ["testing"],
    # Infra handles framework/plumbing; shouldn't import test-only code
    "infra": ["testing"],
    # Utils are low-level shared helpers; must not depend on higher layers
    "utils": ["domain", "ports", "adapters", "infra", "testing"],
}


def get_package_directories() -> list[Path]:
    """Return all package directory paths inside PACKAGES_DIR."""
    if not PACKAGES_DIR.exists():
        return []
    return sorted(p for p in PACKAGES_DIR.iterdir() if p.is_dir())


def get_present_layers(pkg_path: Path) -> set[str]:
    """Detect which hexagonal layers exist in src/<package_name>/."""
    src_pkg_dir = pkg_path / "src" / pkg_path.name
    if not src_pkg_dir.is_dir():
        return set()
    return {layer for layer in HEX_LAYERS if (src_pkg_dir / layer).is_dir()}
