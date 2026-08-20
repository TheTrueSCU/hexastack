"""Synthetic test data generation utilities and deterministic Faker helpers.

Notes/Architectural Intent:
    Provides standardized synthetic realistic data generation for unit, integration,
    and property-based tests. Supports:
    1. Deterministic seeded Faker instances (`seeded_faker(seed=42)`) for 100%
       reproducible test runs compatible with `inline-snapshot`.
    2. Hypothesis custom strategies with semantic Faker providers.
    3. Generic dictionary / model synthetic payload builders.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from hexastack_core.domain.exceptions import MissingDependencyError

if TYPE_CHECKING:
    from faker import Faker

__all__ = [
    "faker_strategy",
    "generate_synthetic_payload",
    "seeded_faker",
]


def faker_strategy(provider_method_name: str, *args: Any, **kwargs: Any) -> Any:
    """Generate a Hypothesis search strategy calling a Faker provider.

    Notes/Architectural Intent:
        Enables seamless integration between Hypothesis fuzz testing and
        semantically rich synthetic data (e.g. valid emails, names, URLs).

    Args:
        provider_method_name: Name of Faker provider (e.g. 'email', 'name', 'ipv4').
        *args: Positional arguments forwarded to provider method.
        **kwargs: Keyword arguments forwarded to provider method.

    Returns:
        Hypothesis search strategy generating synthetic provider outputs.

    Raises:
        MissingDependencyError: If `hypothesis` or `faker` is not installed.
    """
    try:
        from hypothesis import strategies as st
    except ImportError as e:
        raise MissingDependencyError(
            "hypothesis is required for faker_strategy. "
            "Install with 'pip install hypothesis' or 'pip install hexastack[testing]'."
        ) from e

    try:
        from faker import Faker
    except ImportError as e:
        raise MissingDependencyError(
            "faker is required for faker_strategy. "
            "Install with 'pip install faker' or 'pip install hexastack[testing]'."
        ) from e

    fake = Faker()

    def _generate() -> Any:
        provider = getattr(fake, provider_method_name)
        return provider(*args, **kwargs)

    return st.builds(_generate)


def generate_synthetic_payload(
    schema: dict[str, str],
    *,
    seed: int = 42,
) -> dict[str, Any]:
    """Generate a realistic synthetic dictionary payload based on a provider schema mapping.

    Notes/Architectural Intent:
        Convenient one-line fixture generator for integration tests, event payloads,
        and database seeding.

    Args:
        schema: Mapping of field names to Faker provider names (e.g. `{'email': 'safe_email', 'name': 'name'}`).
        seed: Seed value for deterministic output. Defaults to 42.

    Returns:
        Dictionary populated with synthetic values.

    Raises:
        AttributeError: If a requested provider name does not exist on Faker.
        MissingDependencyError: If `faker` is not installed.
    """
    fake = seeded_faker(seed=seed)
    payload: dict[str, Any] = {}

    for field, provider_name in schema.items():
        provider = getattr(fake, provider_name)
        payload[field] = provider()

    return payload


def seeded_faker(seed: int = 42, locale: str | None = None) -> Faker:
    """Create or return a deterministically seeded Faker instance.

    Notes/Architectural Intent:
        Essential for generating realistic strings/data while maintaining 100%
        deterministic outputs required by regression testing and `inline-snapshot`.

    Args:
        seed: Fixed integer seed value. Defaults to 42.
        locale: Optional locale string (e.g. 'en_US', 'de_DE').

    Returns:
        Deterministically seeded Faker generator instance.

    Raises:
        MissingDependencyError: If `faker` is not installed.
    """
    try:
        from faker import Faker
    except ImportError as e:
        raise MissingDependencyError(
            "faker is required for seeded_faker. "
            "Install with 'pip install faker' or 'pip install hexastack[testing]'."
        ) from e

    fake = Faker(locale=locale)
    fake.seed_instance(seed)
    return fake
