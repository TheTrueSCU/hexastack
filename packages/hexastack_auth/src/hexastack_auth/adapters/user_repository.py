"""In-memory adapters for user aggregate persistence and token storage.

Notes/Architectural Intent:
    Provides thread-safe in-memory implementations of UserRepositoryPort and
    TokenStorePort suitable for development, hermetic unit tests, and fast prototyping.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from threading import Lock
from typing import TYPE_CHECKING

from hexastack_auth.ports.user import TokenStorePort, UserRepositoryPort

if TYPE_CHECKING:
    from hexastack_auth.domain.user import User, VerificationToken


class InMemoryUserRepository(UserRepositoryPort):
    """Thread-safe in-memory implementation of UserRepositoryPort.

    Notes/Architectural Intent:
        Stores User domain aggregates indexed by ID, email, and external OAuth provider IDs.
        Guarantees thread-safe access via an internal reentrant Lock.
    """

    def __init__(self) -> None:
        """Initialize in-memory storage maps and lock."""
        self._lock = Lock()
        self._users_by_id: dict[str, User] = {}
        self._users_by_email: dict[str, str] = {}  # email.lower() -> user_id
        self._oauth_index: dict[
            tuple[str, str], str
        ] = {}  # (provider, account_id) -> user_id

    def get_by_id(self, user_id: str) -> User | None:
        """Retrieve user by ID."""
        with self._lock:
            return self._users_by_id.get(user_id)

    async def get_by_id_async(self, user_id: str) -> User | None:
        """Asynchronously retrieve user by ID."""
        return await asyncio.to_thread(self.get_by_id, user_id)

    def get_by_email(self, email: str) -> User | None:
        """Retrieve user by email address."""
        with self._lock:
            user_id = self._users_by_email.get(email.lower().strip())
            return self._users_by_id.get(user_id) if user_id else None

    async def get_by_email_async(self, email: str) -> User | None:
        """Asynchronously retrieve user by email address."""
        return await asyncio.to_thread(self.get_by_email, email)

    def get_by_oauth(self, provider: str, account_id: str) -> User | None:
        """Retrieve user by linked OAuth provider account."""
        with self._lock:
            user_id = self._oauth_index.get((provider.lower(), str(account_id)))
            return self._users_by_id.get(user_id) if user_id else None

    async def get_by_oauth_async(self, provider: str, account_id: str) -> User | None:
        """Asynchronously retrieve user by linked OAuth provider account."""
        return await asyncio.to_thread(self.get_by_oauth, provider, account_id)

    def save(self, user: User) -> User:
        """Persist or update user aggregate and rebuild secondary indices."""
        with self._lock:
            user.updated_at = datetime.now(UTC)
            self._users_by_id[user.id] = user
            self._users_by_email[user.email.lower().strip()] = user.id
            for acc in user.oauth_accounts:
                self._oauth_index[(acc.provider.lower(), str(acc.account_id))] = user.id
            return user

    async def save_async(self, user: User) -> User:
        """Asynchronously persist or update user aggregate."""
        return await asyncio.to_thread(self.save, user)

    def delete(self, user_id: str) -> bool:
        """Delete user by ID and purge secondary indices."""
        with self._lock:
            user = self._users_by_id.pop(user_id, None)
            if user is None:
                return False
            self._users_by_email.pop(user.email.lower().strip(), None)
            for acc in user.oauth_accounts:
                self._oauth_index.pop((acc.provider.lower(), str(acc.account_id)), None)
            return True

    async def delete_async(self, user_id: str) -> bool:
        """Asynchronously delete user by ID."""
        return await asyncio.to_thread(self.delete, user_id)


class InMemoryTokenStore(TokenStorePort):
    """Thread-safe in-memory implementation of TokenStorePort for ephemeral tokens.

    Notes/Architectural Intent:
        Stores VerificationToken instances with single-use invalidation semantics
        and automatic expiration evaluation.
    """

    def __init__(self) -> None:
        """Initialize in-memory token map and lock."""
        self._lock = Lock()
        self._tokens: dict[str, VerificationToken] = {}

    def store_token(self, token: VerificationToken) -> None:
        """Store an ephemeral verification token."""
        with self._lock:
            self._tokens[token.token] = token

    async def store_token_async(self, token: VerificationToken) -> None:
        """Asynchronously store an ephemeral verification token."""
        await asyncio.to_thread(self.store_token, token)

    def get_token(self, token: str) -> VerificationToken | None:
        """Lookup active verification token."""
        with self._lock:
            stored = self._tokens.get(token)
            if stored is None:
                return None
            if stored.is_expired():
                del self._tokens[token]
                return None
            return stored

    async def get_token_async(self, token: str) -> VerificationToken | None:
        """Asynchronously lookup active verification token."""
        return await asyncio.to_thread(self.get_token, token)

    def consume_token(self, token: str) -> VerificationToken | None:
        """Retrieve and immediately invalidate single-use token."""
        with self._lock:
            stored = self._tokens.pop(token, None)
            if stored is None:
                return None
            if stored.is_expired():
                return None
            return stored

    async def consume_token_async(self, token: str) -> VerificationToken | None:
        """Asynchronously retrieve and invalidate single-use token."""
        return await asyncio.to_thread(self.consume_token, token)


__all__ = [
    "InMemoryTokenStore",
    "InMemoryUserRepository",
]
