"""Architectural boundary assertion utilities for Hexagonal Architecture.

Notes/Architectural Intent:
    Provides high-level assertions leveraging `pytest-archon` to verify strict
    Hexagonal Architecture layer boundaries across domain, ports, adapters,
    infra, utils, and testing modules.
"""

from hexastack_core.domain.exceptions import MissingDependencyError

__all__ = [
    "assert_clean_architecture",
    "get_layer_restrictions",
]

# Standard Hexagonal layer restriction mapping: {layer: [forbidden target layers]}
DEFAULT_LAYER_RESTRICTIONS: dict[str, list[str]] = {
    "domain": ["ports", "adapters", "infra", "testing"],
    "ports": ["adapters", "infra", "testing"],
    "adapters": ["testing"],
    "infra": ["testing"],
    "utils": ["domain", "ports", "adapters", "infra", "testing"],
}


def assert_clean_architecture(
    package_name: str,
    *,
    custom_restrictions: dict[str, list[str]] | None = None,
    extra_disallowed: dict[str, list[str]] | None = None,
) -> None:
    """Assert Hexagonal Architecture layer boundaries using pytest-archon.

    Notes/Architectural Intent:
        Validates that inner layers (Domain, Ports) do not leak or import
        from outer layers (Adapters, Infra, Testing) in accordance with the
        Dependency Inversion Principle.

    Args:
        package_name: Root Python package name to inspect (e.g., 'hexastack_cqrs' or 'my_app').
        custom_restrictions: Full override mapping of {source_layer: [forbidden_target_layers]}.
        extra_disallowed: Optional additional forbidden imports to merge onto defaults.

    Raises:
        MissingDependencyError: If `pytest-archon` is not installed.
        AssertionError: If any architectural rule is violated.
    """
    try:
        from pytest_archon import archrule
    except ImportError as e:
        raise MissingDependencyError(
            "pytest-archon is required for assert_clean_architecture. "
            "Install with 'pip install pytest-archon' or 'pip install hexastack[testing]'."
        ) from e

    import importlib.util

    restrictions = custom_restrictions or get_layer_restrictions()
    if extra_disallowed:
        for layer, forbidden in extra_disallowed.items():
            restrictions.setdefault(layer, []).extend(forbidden)

    for layer, disallowed in restrictions.items():
        source_module = f"{package_name}.{layer}"
        # Only check rules for layers that exist in the package
        if importlib.util.find_spec(source_module) is None:
            continue

        target_modules = [
            f"{package_name}.{d}"
            for d in disallowed
            if importlib.util.find_spec(f"{package_name}.{d}") is not None
        ]
        if not target_modules:
            continue

        rule_name = f"{package_name}: {layer} must not import from {disallowed}"
        (
            archrule(rule_name)
            .match(source_module)
            .should_not_import(*target_modules)
            .check(package_name)
        )


def get_layer_restrictions() -> dict[str, list[str]]:
    """Return a copy of the default hexagonal layer import restrictions."""
    return {k: list(v) for k, v in DEFAULT_LAYER_RESTRICTIONS.items()}
