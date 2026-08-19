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

    # 2. When UserContext is present
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
