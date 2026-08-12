from hexastack_core.utils.context import (
    UserContext,
    correlation_id_ctx,
    get_correlation_id,
    get_user_context,
    new_correlation_id,
    set_correlation_id,
    set_user_context,
    user_ctx,
)


def test_context_vars_and_user_context():
    correlation_id_ctx.set("req-12345")
    assert correlation_id_ctx.get() == "req-12345"

    user = UserContext(user_id="u-99", roles=["admin", "user"], tenant_id="tenant-1")
    user_ctx.set(user)

    retrieved = user_ctx.get()
    assert retrieved is not None
    assert retrieved.user_id == "u-99"
    assert retrieved.roles == ["admin", "user"]
    assert retrieved.tenant_id == "tenant-1"


def test_context_helper_functions():
    # Test set_correlation_id and get_correlation_id
    token = set_correlation_id("test-corr-id")
    assert get_correlation_id() == "test-corr-id"
    correlation_id_ctx.reset(token)

    # Test new_correlation_id
    generated_id = new_correlation_id()
    assert len(generated_id) > 0
    assert get_correlation_id() == generated_id

    # Test set_user_context and get_user_context
    user = UserContext(user_id="u-100", roles=["viewer"])
    user_token = set_user_context(user)
    assert get_user_context() == user
    set_user_context(None)
    assert get_user_context() is None
    user_ctx.reset(user_token)
