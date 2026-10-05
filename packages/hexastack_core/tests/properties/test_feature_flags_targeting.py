"""Property-based tests for feature flag evaluation context and details invariants.

Notes/Architectural Intent:
    Verifies that FlagEvaluationReason string representation matches exact CNCF OpenFeature values,
    EvaluationContext preserves all targeting parameters (user, tenant, targeting_key, attributes),
    and ambient UserContext extraction maintains sorted role tuple idempotency.
"""

from __future__ import annotations

from typing import Any

from hypothesis import given
from hypothesis import strategies as st

from hexastack_core.domain.feature_flags import (
    EvaluationContext,
    FlagEvaluationDetails,
    FlagEvaluationReason,
)
from hexastack_core.utils.context import UserContext, set_user_context


def test_flag_evaluation_reason_str_roundtrip() -> None:
    """Verify all FlagEvaluationReason enum variants have exact string values."""
    expected = {
        "STATIC": FlagEvaluationReason.STATIC,
        "DEFAULT": FlagEvaluationReason.DEFAULT,
        "TARGETING_MATCH": FlagEvaluationReason.TARGETING_MATCH,
        "SPLIT": FlagEvaluationReason.SPLIT,
        "CACHED": FlagEvaluationReason.CACHED,
        "DISABLED": FlagEvaluationReason.DISABLED,
        "UNKNOWN": FlagEvaluationReason.UNKNOWN,
        "ERROR": FlagEvaluationReason.ERROR,
    }
    for key, enum_val in expected.items():
        assert str(enum_val) == key
        assert enum_val.value == key
        assert FlagEvaluationReason(key) is enum_val


@given(
    targeting_key=st.one_of(st.none(), st.text(min_size=1, max_size=30)),
    user_id=st.one_of(st.none(), st.text(min_size=1, max_size=30)),
    tenant_id=st.one_of(st.none(), st.text(min_size=1, max_size=30)),
    roles=st.lists(st.text(min_size=1, max_size=20), max_size=5),
    attributes=st.dictionaries(
        st.text(min_size=1, max_size=15),
        st.one_of(st.integers(), st.floats(allow_nan=False), st.booleans(), st.text()),
        max_size=5,
    ),
)
def test_evaluation_context_property_invariants(
    targeting_key: str | None,
    user_id: str | None,
    tenant_id: str | None,
    roles: list[str],
    attributes: dict[str, Any],
) -> None:
    """Verify EvaluationContext preserves explicit initialization attributes."""
    ctx = EvaluationContext(
        targeting_key=targeting_key,
        user_id=user_id,
        tenant_id=tenant_id,
        roles=tuple(roles),
        attributes=attributes,
    )
    assert ctx.targeting_key == targeting_key
    assert ctx.user_id == user_id
    assert ctx.tenant_id == tenant_id
    assert ctx.roles == tuple(roles)
    assert ctx.attributes == attributes


@given(
    user_id=st.text(min_size=1, max_size=30),
    tenant_id=st.one_of(st.none(), st.text(min_size=1, max_size=30)),
    roles=st.lists(st.text(min_size=1, max_size=20), max_size=5),
    extra_attr_key=st.text(
        min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"
    ),
    extra_attr_val=st.text(min_size=1, max_size=20),
)
def test_evaluation_context_ambient_resolution_property(
    user_id: str,
    tenant_id: str | None,
    roles: list[str],
    extra_attr_key: str,
    extra_attr_val: str,
) -> None:
    """Verify ambient UserContext extraction accurately propagates into EvaluationContext."""
    try:
        uctx = UserContext(
            user_id=user_id,
            tenant_id=tenant_id,
            roles=roles,
        )
        set_user_context(uctx)
        eval_ctx = EvaluationContext.from_current_context(
            **{extra_attr_key: extra_attr_val}
        )

        assert eval_ctx.user_id == user_id
        assert eval_ctx.tenant_id == tenant_id
        assert eval_ctx.targeting_key == (user_id or tenant_id)
        assert eval_ctx.roles == tuple(sorted(roles))
        assert eval_ctx.attributes[extra_attr_key] == extra_attr_val
    finally:
        set_user_context(None)


@given(
    flag_key=st.text(min_size=1, max_size=30),
    val=st.one_of(st.booleans(), st.integers(), st.floats(allow_nan=False), st.text()),
    reason=st.sampled_from(list(FlagEvaluationReason)),
    variant=st.one_of(st.none(), st.text(min_size=1, max_size=20)),
    error_code=st.one_of(st.none(), st.text(min_size=1, max_size=20)),
    error_message=st.one_of(st.none(), st.text(min_size=1, max_size=50)),
)
def test_flag_evaluation_details_frozen_property(
    flag_key: str,
    val: Any,
    reason: FlagEvaluationReason,
    variant: str | None,
    error_code: str | None,
    error_message: str | None,
) -> None:
    """Verify FlagEvaluationDetails preserves metadata fields in immutable structure."""
    details = FlagEvaluationDetails(
        flag_key=flag_key,
        value=val,
        reason=reason,
        variant=variant,
        error_code=error_code,
        error_message=error_message,
    )
    assert details.flag_key == flag_key
    assert details.value == val
    assert details.reason == reason
    assert details.variant == variant
    assert details.error_code == error_code
    assert details.error_message == error_message
