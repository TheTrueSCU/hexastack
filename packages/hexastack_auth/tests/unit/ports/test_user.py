from hexastack_auth.domain.user import OAuthUserInfo, User, VerificationToken
from hexastack_auth.ports.user import (
    OAuthProviderPort,
    TokenStorePort,
    UserRepositoryPort,
)


class DummyUserRepo(UserRepositoryPort):
    def get_by_id(self, user_id: str) -> User | None:
        return User(email="test@user.com", id=user_id)

    async def get_by_id_async(self, user_id: str) -> User | None:
        return self.get_by_id(user_id)

    def get_by_email(self, email: str) -> User | None:
        return User(email=email)

    async def get_by_email_async(self, email: str) -> User | None:
        return self.get_by_email(email)

    def get_by_oauth(self, provider: str, account_id: str) -> User | None:
        return User(email="oauth@user.com")

    async def get_by_oauth_async(self, provider: str, account_id: str) -> User | None:
        return self.get_by_oauth(provider, account_id)

    def save(self, user: User) -> User:
        return user

    async def save_async(self, user: User) -> User:
        return user

    def delete(self, user_id: str) -> bool:
        return True

    async def delete_async(self, user_id: str) -> bool:
        return True


class DummyTokenStore(TokenStorePort):
    def store_token(self, token: VerificationToken) -> None:
        pass

    async def store_token_async(self, token: VerificationToken) -> None:
        pass

    def get_token(self, token: str) -> VerificationToken | None:
        return None

    async def get_token_async(self, token: str) -> VerificationToken | None:
        return None

    def consume_token(self, token: str) -> VerificationToken | None:
        return None

    async def consume_token_async(self, token: str) -> VerificationToken | None:
        return None


class DummyOAuthProvider(OAuthProviderPort):
    @property
    def name(self) -> str:
        return "dummy"

    def get_authorization_url(self, state: str, redirect_uri: str) -> str:
        return f"https://example.com/auth?state={state}"

    async def exchange_code(self, code: str, redirect_uri: str) -> OAuthUserInfo:
        return OAuthUserInfo(
            provider="dummy", account_id="acc-1", email="user@dummy.com"
        )


async def test_dummy_user_ports():
    repo = DummyUserRepo()
    u = repo.get_by_id("u1")
    assert u is not None
    assert u.id == "u1"

    u_async = await repo.get_by_id_async("u2")
    assert u_async is not None
    assert u_async.id == "u2"

    u_email = repo.get_by_email("test@user.com")
    assert u_email is not None

    u_oauth = await repo.get_by_oauth_async("google", "123")
    assert u_oauth is not None

    saved = repo.save(u)
    assert saved.id == "u1"

    deleted = await repo.delete_async("u1")
    assert deleted is True

    t_store = DummyTokenStore()
    t = t_store.get_token("tok")
    assert t is None

    prov = DummyOAuthProvider()
    assert prov.name == "dummy"
    url = prov.get_authorization_url("st", "http://callback")
    assert "state=st" in url
    info = await prov.exchange_code("code", "http://callback")
    assert info.email == "user@dummy.com"
