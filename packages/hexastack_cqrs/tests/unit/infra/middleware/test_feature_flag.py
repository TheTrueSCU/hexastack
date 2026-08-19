import pytest

from hexastack_core.adapters.feature_flags.in_memory import InMemoryFeatureFlagAdapter
from hexastack_core.domain import Command
from hexastack_cqrs.infra.decorators import feature_flag
from hexastack_cqrs.infra.middleware.feature_flag import (
    ConditionalFeatureFlagMiddleware,
    FeatureFlagDisabledError,
)


class SampleCommand(Command):
    amount: int


def test_conditional_feature_flag_middleware_enabled():
    flags = InMemoryFeatureFlagAdapter({"feature.transfer": True})
    mw = ConditionalFeatureFlagMiddleware(flags, "feature.transfer")

    cmd = SampleCommand(amount=100)
    result = mw(cmd, lambda c: c.amount * 2)
    assert result == 200


def test_conditional_feature_flag_middleware_disabled_bypass():
    flags = InMemoryFeatureFlagAdapter({"feature.transfer": False})
    mw = ConditionalFeatureFlagMiddleware(
        flags, "feature.transfer", bypass_on_disabled=True
    )

    cmd = SampleCommand(amount=100)
    result = mw(cmd, lambda c: c.amount * 3)
    assert result == 300


def test_conditional_feature_flag_middleware_disabled_fallback():
    flags = InMemoryFeatureFlagAdapter({"feature.transfer": False})
    mw = ConditionalFeatureFlagMiddleware(
        flags,
        "feature.transfer",
        fallback=lambda c: f"fallback_{c.amount}",
    )

    cmd = SampleCommand(amount=100)
    result = mw(cmd, lambda c: c.amount * 2)
    assert result == "fallback_100"


def test_conditional_feature_flag_middleware_disabled_raises():
    flags = InMemoryFeatureFlagAdapter({"feature.transfer": False})
    mw = ConditionalFeatureFlagMiddleware(
        flags, "feature.transfer", bypass_on_disabled=False
    )

    cmd = SampleCommand(amount=100)
    with pytest.raises(FeatureFlagDisabledError, match="is disabled"):
        mw(cmd, lambda c: c.amount * 2)


def test_feature_flag_decorator_enabled_and_fallback():
    flags = InMemoryFeatureFlagAdapter({"feature.checkout_v2": True})

    @feature_flag("feature.checkout_v2", fallback=lambda c, **kw: "legacy")
    def checkout_handler(cmd: SampleCommand, **kw) -> str:
        return f"modern_{cmd.amount}"

    # Enabled
    res_enabled = checkout_handler(SampleCommand(amount=50), __feature_flags__=flags)
    assert res_enabled == "modern_50"

    # Disabled -> Fallback
    flags.set_flag("feature.checkout_v2", False)
    res_disabled = checkout_handler(SampleCommand(amount=50), __feature_flags__=flags)
    assert res_disabled == "legacy"


def test_feature_flag_decorator_disabled_raises():
    flags = InMemoryFeatureFlagAdapter({"feature.checkout_v2": False})

    @feature_flag("feature.checkout_v2")
    def checkout_handler(cmd: SampleCommand, **kw) -> str:
        return f"modern_{cmd.amount}"

    with pytest.raises(FeatureFlagDisabledError):
        checkout_handler(SampleCommand(amount=50), __feature_flags__=flags)
