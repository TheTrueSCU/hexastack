from datetime import UTC, datetime, timedelta

from hexastack_auth.adapters.user_repository import (
    InMemoryTokenStore,
    InMemoryUserRepository,
)
from hexastack_auth.domain.user import OAuthAccount, User, VerificationToken


def test_in_memory_user_repository_crud():
    repo = InMemoryUserRepository()
    user = User(
        email="test@example.com",
        roles=frozenset({"user"}),
        oauth_accounts=[
            OAuthAccount(provider="github", account_id="gh-77", user_id="placeholder")
        ],
    )

    saved = repo.save(user)
    assert saved.id == user.id

    by_id = repo.get_by_id(user.id)
    assert by_id is not None
    assert by_id.email == "test@example.com"

    by_email = repo.get_by_email("TEST@example.com")
    assert by_email is not None
    assert by_email.id == user.id

    by_oauth = repo.get_by_oauth("github", "gh-77")
    assert by_oauth is not None
    assert by_oauth.id == user.id

    # Non-existent
    assert repo.get_by_id("non-existent") is None
    assert repo.get_by_email("unknown@user.com") is None
    assert repo.get_by_oauth("google", "missing") is None

    # Delete
    deleted = repo.delete(user.id)
    assert deleted is True
    assert repo.get_by_id(user.id) is None
    assert repo.get_by_email("test@example.com") is None
    assert repo.get_by_oauth("github", "gh-77") is None
    assert repo.delete("non-existent") is False


async def test_in_memory_user_repository_async():
    repo = InMemoryUserRepository()
    user = User(email="async@example.com")
    await repo.save_async(user)

    fetched = await repo.get_by_email_async("async@example.com")
    assert fetched is not None
    assert fetched.id == user.id

    by_id = await repo.get_by_id_async(user.id)
    assert by_id is not None

    deleted = await repo.delete_async(user.id)
    assert deleted is True


def test_in_memory_token_store_lifecycle():
    store = InMemoryTokenStore()
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    token = VerificationToken(
        token="token-xyz",
        user_id="user-123",
        token_type="email_verification",
        expires_at=expires_at,
    )

    store.store_token(token)

    fetched = store.get_token("token-xyz")
    assert fetched is not None
    assert fetched.token == "token-xyz"

    consumed = store.consume_token("token-xyz")
    assert consumed is not None
    assert consumed.user_id == "user-123"

    # Consuming again returns None (single-use)
    consumed_again = store.consume_token("token-xyz")
    assert consumed_again is None


def test_in_memory_token_store_expiration():
    store = InMemoryTokenStore()
    past = datetime.now(UTC) - timedelta(minutes=5)
    expired_token = VerificationToken(
        token="expired-token",
        user_id="user-456",
        token_type="password_reset",
        expires_at=past,
    )
    store.store_token(expired_token)

    assert store.get_token("expired-token") is None
    assert store.consume_token("expired-token") is None


async def test_in_memory_token_store_async():
    store = InMemoryTokenStore()
    token = VerificationToken(
        token="tok-async",
        user_id="u-async",
        token_type="email_verification",
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )
    await store.store_token_async(token)

    fetched = await store.get_token_async("tok-async")
    assert fetched is not None

    consumed = await store.consume_token_async("tok-async")
    assert consumed is not None
