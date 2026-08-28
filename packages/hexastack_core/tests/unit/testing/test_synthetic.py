"""Unit and property tests for synthetic test data utilities (Faker + Inline Snapshot + Hypothesis)."""

from dataclasses import dataclass

from hypothesis import given
from inline_snapshot import snapshot

from hexastack_core.testing import (
    faker_strategy,
    generate_synthetic_payload,
    seeded_faker,
)


@dataclass(frozen=True)
class UserRegistration:
    email: str
    username: str


def test_seeded_faker_deterministic_reproducibility():
    """Verify seeded_faker produces 100% deterministic output across calls."""
    fake1 = seeded_faker(seed=1337)
    val1 = (fake1.first_name(), fake1.safe_email(), fake1.city())

    fake2 = seeded_faker(seed=1337)
    val2 = (fake2.first_name(), fake2.safe_email(), fake2.city())

    assert val1 == val2


def test_seeded_faker_inline_snapshot_compatibility():
    """Verify seeded_faker works seamlessly with inline-snapshot without churn."""
    fake = seeded_faker(seed=42)

    user_data = {
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "email": fake.safe_email(),
    }

    assert user_data == snapshot(
        {
            "first_name": "Danielle",
            "last_name": "Johnson",
            "email": "john21@example.net",
        }
    )


def test_generate_synthetic_payload():
    """Verify generate_synthetic_payload creates structured dicts from provider schemas."""
    schema = {
        "user_id": "uuid4",
        "email": "safe_email",
        "country": "country",
    }
    payload = generate_synthetic_payload(schema, seed=123)

    assert "user_id" in payload
    assert "email" in payload
    assert "country" in payload
    assert "@" in payload["email"]


@given(email=faker_strategy("safe_email"))
def test_faker_strategy_hypothesis_fuzz(email: str):
    """Verify faker_strategy generates valid synthetic email inputs during hypothesis fuzzing."""
    assert isinstance(email, str)
    assert "@" in email
    assert email.endswith((".org", ".com", ".net"))
