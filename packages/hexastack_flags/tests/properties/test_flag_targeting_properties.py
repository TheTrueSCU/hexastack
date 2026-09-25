"""Property-based tests for OpenFeature flag adapter and context translation.

Notes/Architectural Intent:
    Verifies domain invariants of ambient evaluation context mapping and
    guaranteed default value fallback resilience under arbitrary inputs and
    OpenFeature provider backends using Hypothesis.
"""

import openfeature.api
from hypothesis import given, settings
from hypothesis import strategies as st
from openfeature.provider.in_memory_provider import InMemoryFlag, InMemoryProvider

from hexastack_core.domain.feature_flags import EvaluationContext
from hexastack_flags.adapters.openfeature import (
    OpenFeatureFlagAdapter,
    _to_openfeature_context,
)

# Custom Hypothesis Strategies for Feature Flags Context
st_roles = st.lists(st.from_regex(r"[a-z_]{2,15}", fullmatch=True), max_size=5)
st_attributes = st.dictionaries(
    keys=st.from_regex(r"[a-z_]{2,15}", fullmatch=True),
    values=st.one_of(st.booleans(), st.integers(-1000, 1000), st.text(max_size=30)),
    max_size=5,
)

st_eval_context = st.builds(
    EvaluationContext,
    user_id=st.one_of(st.none(), st.from_regex(r"usr_[0-9]{3,6}", fullmatch=True)),
    tenant_id=st.one_of(st.none(), st.from_regex(r"org_[0-9]{3,6}", fullmatch=True)),
    targeting_key=st.one_of(
        st.none(), st.from_regex(r"tgt_[0-9]{3,6}", fullmatch=True)
    ),
    roles=st_roles,
    attributes=st_attributes,
)


@given(ctx=st_eval_context)
@settings(max_examples=50)
def test_evaluation_context_translation_preserves_attributes(
    ctx: EvaluationContext,
) -> None:
    """Property test verifying context conversion preserves all fields without data loss.

    Args:
        ctx: Generated EvaluationContext instance.

    Notes/Architectural Intent:
        Guarantees that translating Hexastack ambient context to CNCF OpenFeature
        context preserves targeting keys, identity fields, roles, and custom attributes.
    """
    of_ctx = _to_openfeature_context(ctx)
    assert of_ctx is not None

    expected_targeting = ctx.targeting_key or ctx.user_id or ""
    assert of_ctx.targeting_key == expected_targeting

    # Verify identity fields
    if ctx.user_id:
        assert of_ctx.attributes.get("user_id") == ctx.user_id
    if ctx.tenant_id:
        assert of_ctx.attributes.get("tenant_id") == ctx.tenant_id
    if ctx.roles:
        assert of_ctx.attributes.get("roles") == list(ctx.roles)

    # Verify custom attributes
    for k, v in ctx.attributes.items():
        assert of_ctx.attributes.get(k) == v


@given(
    flag_key=st.from_regex(r"flag_[a-z0-9_]{3,20}", fullmatch=True),
    default_bool=st.booleans(),
    default_str=st.text(max_size=30),
    default_int=st.integers(-5000, 5000),
    default_float=st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False),
)
@settings(max_examples=40)
def test_unconfigured_flags_strictly_return_defaults(
    flag_key: str,
    default_bool: bool,
    default_str: str,
    default_int: int,
    default_float: float,
) -> None:
    """Property test verifying fallback guarantees when evaluating unknown flags.

    Args:
        flag_key: Generated non-existent flag name.
        default_bool: Generated default boolean.
        default_str: Generated default string.
        default_int: Generated default integer.
        default_float: Generated default float.

    Notes/Architectural Intent:
        Asserts that unknown or missing feature flags strictly return the provided
        default value without raising unexpected exceptions.
    """
    domain_name = f"unconf_{flag_key[:10]}"
    provider = InMemoryProvider(flags={})
    openfeature.api.set_provider(provider, domain=domain_name)
    client = openfeature.api.get_client(domain_name)

    adapter = OpenFeatureFlagAdapter(client=client)

    # Boolean
    b_val = adapter.is_enabled(flag_key, default=default_bool)
    assert b_val == default_bool

    # String
    s_val = adapter.get_string_value(flag_key, default=default_str)
    assert s_val == default_str

    # Integer
    i_val = adapter.get_integer_value(flag_key, default=default_int)
    assert i_val == default_int

    # Float
    f_val = adapter.get_float_value(flag_key, default=default_float)
    assert f_val == default_float


@given(
    flag_key=st.from_regex(r"flag_[a-z0-9_]{3,15}", fullmatch=True),
    active_val=st.booleans(),
)
@settings(max_examples=30)
def test_configured_boolean_flag_evaluates_exact_state(
    flag_key: str, active_val: bool
) -> None:
    """Property test verifying configured flag values evaluate faithfully.

    Args:
        flag_key: Configured flag identifier.
        active_val: Expected boolean value.

    Notes/Architectural Intent:
        Validates that configured flag states in the provider are returned directly,
        satisfying round-trip fidelity between provider definition and adapter output.
    """
    variant_name = "on" if active_val else "off"
    flags = {
        flag_key: InMemoryFlag(
            default_variant=variant_name,
            variants={"on": True, "off": False},
        )
    }
    domain_name = f"conf_{flag_key}"
    provider = InMemoryProvider(flags=flags)
    openfeature.api.set_provider(provider, domain=domain_name)
    client = openfeature.api.get_client(domain_name)

    adapter = OpenFeatureFlagAdapter(client=client)

    # Evaluating with opposite default confirms the returned value came from the provider
    res = adapter.get_boolean_value(flag_key, default=not active_val)
    assert res == active_val
