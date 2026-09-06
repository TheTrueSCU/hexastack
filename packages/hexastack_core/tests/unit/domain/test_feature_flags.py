from hexastack_core.domain.feature_flags import (
    EvaluationContext,
    FlagEvaluationDetails,
    FlagEvaluationReason,
)
from hexastack_core.utils.context import UserContext, set_user_context


def test_evaluation_context_defaults():
    ctx = EvaluationContext()
    assert ctx.targeting_key is None
    assert ctx.user_id is None
    assert ctx.tenant_id is None
    assert ctx.roles == ()
    assert ctx.attributes == {}


def test_evaluation_context_from_current_context():
    # 1. When no UserContext set
    set_user_context(None)
    ctx1 = EvaluationContext.from_current_context(region="us-east-1")
    assert ctx1.user_id is None
    assert ctx1.attributes == {"region": "us-east-1"}

    # 2. When UserContext is present with user_id
    uctx = UserContext(
        user_id="usr-123",
        tenant_id="tenant-abc",
        roles=["viewer", "admin"],
    )
    set_user_context(uctx)

    ctx2 = EvaluationContext.from_current_context(tier="premium")
    assert ctx2.targeting_key == "usr-123"
    assert ctx2.user_id == "usr-123"
    assert ctx2.tenant_id == "tenant-abc"
    assert ctx2.roles == ("admin", "viewer")
    assert ctx2.attributes["tier"] == "premium"

    # 3. When UserContext is present with tenant_id only (no user_id)
    uctx3 = UserContext(
        user_id="",
        tenant_id="tenant-only-99",
    )
    set_user_context(uctx3)
    ctx3 = EvaluationContext.from_current_context()
    assert ctx3.targeting_key == "tenant-only-99"

    set_user_context(None)


def test_flag_evaluation_details():
    details = FlagEvaluationDetails[bool](
        flag_key="beta_feature",
        value=True,
        reason=FlagEvaluationReason.TARGETING_MATCH,
        variant="v1",
    )
    assert details.flag_key == "beta_feature"
    assert details.value is True
    assert details.reason == FlagEvaluationReason.TARGETING_MATCH
    assert details.variant == "v1"

    default_details = FlagEvaluationDetails[int](flag_key="num_retries", value=3)
    assert default_details.reason == FlagEvaluationReason.UNKNOWN
    assert default_details.variant is None
    assert default_details.error_code is None
    assert default_details.error_message is None

    # Test FlagEvaluationReason enum values
    assert FlagEvaluationReason.STATIC == "STATIC"
    assert FlagEvaluationReason.DEFAULT == "DEFAULT"
    assert FlagEvaluationReason.SPLIT == "SPLIT"
    assert FlagEvaluationReason.CACHED == "CACHED"
    assert FlagEvaluationReason.DISABLED == "DISABLED"
    assert FlagEvaluationReason.ERROR == "ERROR"
