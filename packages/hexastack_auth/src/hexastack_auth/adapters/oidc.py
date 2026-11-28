"""OIDC discovery and asymmetric JWKS JWT verification adapters.

Notes/Architectural Intent:
    Implements ``discover_oidc_configuration`` / ``discover_oidc_configuration_async``
    and ``JwksOidcSecurityAdapter`` (``SecurityPort``) using ``PyJWKClient`` for
    key-ID lookup, caching, and live key-rotation retries while enforcing strict
    access-token vs. ID-token confusion defenses.
"""

from __future__ import annotations

import hmac
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import jwt

from hexastack_auth.domain.exceptions import (
    AuthError,
    InvalidTokenError,
    OAuthProviderError,
    TokenExpiredError,
)
from hexastack_auth.domain.models import Identity
from hexastack_auth.domain.oidc import (
    DEFAULT_ASYMMETRIC_OIDC_ALGORITHMS,
    OidcDiscoveryDocument,
    OidcTokenPolicy,
)
from hexastack_auth.ports.security import SecurityPort
from hexastack_core.utils.imports import require_dependency


def _require_httpx() -> Any:
    """Resolve optional httpx dependency for OIDC discovery requests."""
    return require_dependency(
        "httpx",
        extra="oidc",
        package="hexastack-auth",
        feature_name="OIDC discovery",
    )


def _validate_http_url(url: str, *, field_name: str) -> str:
    """Validate that a remote OIDC/JWKS endpoint uses an HTTP(S) URL.

    Args:
        url: Endpoint URL string to validate.
        field_name: Descriptive field name used in validation errors.

    Returns:
        Stripped HTTP or HTTPS URL string.

    Raises:
        ValueError: If the URL is blank, lacks a network location, or uses a
            non-HTTP scheme (e.g. ``file://``).

    Notes/Architectural Intent:
        Prevents SSRF / local file read via ``PyJWKClient``'s underlying
        ``urllib.request`` handler, which would otherwise accept ``file://`` URIs.
    """
    cleaned = url.strip()
    if not cleaned:
        msg = f"OIDC '{field_name}' URL cannot be empty."
        raise ValueError(msg)
    parsed = urlparse(cleaned)
    if parsed.scheme.casefold() not in {"http", "https"} or not parsed.netloc:
        msg = (
            f"OIDC '{field_name}' must be an 'http://' or 'https://' URL, got {url!r}."
        )
        raise ValueError(msg)
    return cleaned


def _resolve_discovery_url(issuer_or_url: str) -> str:
    """Normalize an issuer base URL or explicit discovery URL."""
    validated = _validate_http_url(issuer_or_url, field_name="discovery_url")
    if validated.rstrip("/").endswith("/.well-known/openid-configuration"):
        return validated
    return f"{validated.rstrip('/')}/.well-known/openid-configuration"


def _validate_discovery_urls(doc: OidcDiscoveryDocument) -> OidcDiscoveryDocument:
    """Ensure discovery endpoints are safe HTTP(S) URLs."""
    _validate_http_url(doc.issuer, field_name="issuer")
    _validate_http_url(doc.authorization_endpoint, field_name="authorization_endpoint")
    _validate_http_url(doc.token_endpoint, field_name="token_endpoint")
    _validate_http_url(doc.jwks_uri, field_name="jwks_uri")
    if doc.userinfo_endpoint is not None:
        _validate_http_url(doc.userinfo_endpoint, field_name="userinfo_endpoint")
    return doc


def _parse_discovery_response(response: Any) -> OidcDiscoveryDocument:
    """Validate HTTP status, decode JSON, and construct discovery document."""
    if response.status_code != 200:
        msg = (
            f"OIDC discovery request failed: "
            f"{response.status_code} {getattr(response, 'text', '')}"
        )
        raise OAuthProviderError("oidc", msg)
    try:
        payload = response.json()
    except Exception as exc:
        msg = f"OIDC discovery response was not valid JSON: {exc}"
        raise OAuthProviderError("oidc", msg) from exc
    if not isinstance(payload, Mapping):
        msg = "OIDC discovery response JSON must be an object."
        raise OAuthProviderError("oidc", msg)
    doc = OidcDiscoveryDocument.from_dict(payload)
    return _validate_discovery_urls(doc)


def discover_oidc_configuration(
    issuer_or_url: str,
    *,
    timeout: float = 5.0,
    http_client: Any | None = None,
) -> OidcDiscoveryDocument:
    """Fetch and parse ``/.well-known/openid-configuration`` synchronously.

    Args:
        issuer_or_url: Provider issuer base URL or full discovery document URL.
        timeout: HTTP request timeout in seconds (default 5.0).
        http_client: Optional preconfigured synchronous ``httpx.Client``-like object.

    Returns:
        Validated ``OidcDiscoveryDocument`` containing provider endpoints and
        ``jwks_uri``.

    Raises:
        ValueError: If ``issuer_or_url`` or any discovered endpoint is not HTTP(S)
            or required metadata fields are missing.
        OAuthProviderError: If the HTTP request fails or returns invalid JSON.

    Notes/Architectural Intent:
        Supports caller-injected HTTP clients for deterministic unit testing and
        shared connection pooling while enforcing HTTP(S) scheme safety upfront.
    """
    target_url = _resolve_discovery_url(issuer_or_url)
    httpx = _require_httpx()
    headers = {"Accept": "application/json"}
    try:
        if http_client is not None:
            response = http_client.get(target_url, headers=headers, timeout=timeout)
        else:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(target_url, headers=headers)
    except OAuthProviderError:
        raise
    except Exception as exc:
        msg = f"OIDC discovery fetch failed for '{target_url}': {exc}"
        raise OAuthProviderError("oidc", msg) from exc
    return _parse_discovery_response(response)


async def discover_oidc_configuration_async(
    issuer_or_url: str,
    *,
    timeout: float = 5.0,
    http_client: Any | None = None,
) -> OidcDiscoveryDocument:
    """Fetch and parse ``/.well-known/openid-configuration`` asynchronously.

    Args:
        issuer_or_url: Provider issuer base URL or full discovery document URL.
        timeout: HTTP request timeout in seconds (default 5.0).
        http_client: Optional preconfigured async ``httpx.AsyncClient``-like object.

    Returns:
        Validated ``OidcDiscoveryDocument`` containing provider endpoints and
        ``jwks_uri``.

    Raises:
        ValueError: If ``issuer_or_url`` or any discovered endpoint is not HTTP(S)
            or required metadata fields are missing.
        OAuthProviderError: If the HTTP request fails or returns invalid JSON.

    Notes/Architectural Intent:
        Async twin of ``discover_oidc_configuration`` avoiding blocking event
        loops during FastAPI lifespan startup or dynamic IdP initialization.
    """
    target_url = _resolve_discovery_url(issuer_or_url)
    httpx = _require_httpx()
    headers = {"Accept": "application/json"}
    try:
        if http_client is not None:
            response = await http_client.get(
                target_url, headers=headers, timeout=timeout
            )
        else:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(target_url, headers=headers)
    except OAuthProviderError:
        raise
    except Exception as exc:
        msg = f"Async OIDC discovery fetch failed for '{target_url}': {exc}"
        raise OAuthProviderError("oidc", msg) from exc
    return _parse_discovery_response(response)


def _extract_str_collection(value: Any) -> frozenset[str]:
    """Normalize sequence or whitespace-delimited claim values to ``frozenset[str]``."""
    if value is None:
        return frozenset()
    if isinstance(value, str):
        return frozenset(part for part in value.split() if part)
    if isinstance(value, (list, tuple, set, frozenset)):
        return frozenset(
            str(item) for item in value if item is not None and str(item).strip()
        )
    return frozenset()


class JwksOidcSecurityAdapter(SecurityPort):
    """Concrete ``SecurityPort`` verifying OIDC JWTs via remote JWKS endpoints.

    Notes/Architectural Intent:
        Decouples OIDC resource-server token verification from vendor SDKs using
        ``jwt.PyJWKClient`` and ``OidcTokenPolicy``. Enforces asymmetric signatures,
        automatic single-retry cache refresh on key rotation, and strict
        separation between OAuth2 access tokens and OIDC ID tokens.
    """

    def __init__(
        self,
        jwks_uri: str,
        issuer: str,
        audience: str | tuple[str, ...],
        *,
        allowed_algorithms: tuple[str, ...] = DEFAULT_ASYMMETRIC_OIDC_ALGORITHMS,
        require_access_token_typ: bool = False,
        reject_id_tokens: bool = True,
        jwks_cache_ttl_seconds: int = 300,
        jwks_timeout_seconds: float = 5.0,
        roles_claim: str = "roles",
        permissions_claim: str = "permissions",
        tenant_claim: str = "tenant_id",
        leeway_seconds: int = 30,
        jwk_client: Any | None = None,
    ) -> None:
        """Initialize ``JwksOidcSecurityAdapter``.

        Args:
            jwks_uri: HTTP(S) URL of the provider's JSON Web Key Set endpoint.
            issuer: Expected ``iss`` claim identifying the OIDC provider.
            audience: Expected ``aud`` claim (single string or tuple of strings).
            allowed_algorithms: Allowed asymmetric signing algorithms.
            require_access_token_typ: Require RFC 9068 ``typ: at+jwt`` header when True.
            reject_id_tokens: Reject OIDC ID tokens presented as bearer access tokens.
            jwks_cache_ttl_seconds: JWKS cache lifespan in seconds (default 300).
            jwks_timeout_seconds: HTTP timeout for fetching JWKS keys (default 5.0).
            roles_claim: JWT claim containing user roles.
            permissions_claim: JWT claim containing user permissions.
            tenant_claim: JWT claim containing tenant identifier.
            leeway_seconds: Clock-skew leeway in seconds for ``exp`` checks.
            jwk_client: Optional custom JWK client for hermetic unit testing.

        Raises:
            ValueError: If ``jwks_uri`` is not HTTP(S) or ``OidcTokenPolicy`` fails
                validation (e.g. symmetric ``HS*`` or ``none`` algorithms).
        """
        self._jwks_uri = _validate_http_url(jwks_uri, field_name="jwks_uri")
        self._policy = OidcTokenPolicy(
            issuer=issuer,
            audience=audience,
            allowed_algorithms=allowed_algorithms,
            require_access_token_typ=require_access_token_typ,
            reject_id_tokens=reject_id_tokens,
            roles_claim=roles_claim,
            permissions_claim=permissions_claim,
            tenant_claim=tenant_claim,
            leeway_seconds=leeway_seconds,
        )
        self._jwks_cache_ttl_seconds = jwks_cache_ttl_seconds
        self._jwks_timeout_seconds = jwks_timeout_seconds
        self._custom_jwk_client = jwk_client is not None
        self._jwk_client = jwk_client or self._build_jwk_client()

    def _build_jwk_client(self) -> jwt.PyJWKClient:
        """Construct a caching ``PyJWKClient`` instance."""
        return jwt.PyJWKClient(
            self._jwks_uri,
            cache_jwk_set=True,
            lifespan=self._jwks_cache_ttl_seconds,
            timeout=int(max(1, self._jwks_timeout_seconds)),
        )

    @classmethod
    def from_discovery(
        cls,
        discovery_url: str,
        *,
        audience: str | tuple[str, ...],
        allowed_algorithms: tuple[str, ...] = DEFAULT_ASYMMETRIC_OIDC_ALGORITHMS,
        require_access_token_typ: bool = False,
        reject_id_tokens: bool = True,
        jwks_cache_ttl_seconds: int = 300,
        jwks_timeout_seconds: float = 5.0,
        roles_claim: str = "roles",
        permissions_claim: str = "permissions",
        tenant_claim: str = "tenant_id",
        leeway_seconds: int = 30,
        http_client: Any | None = None,
        jwk_client: Any | None = None,
    ) -> JwksOidcSecurityAdapter:
        """Construct adapter dynamically from ``/.well-known/openid-configuration``.

        Args:
            discovery_url: Issuer URL or explicit OIDC discovery endpoint URL.
            audience: Expected resource-server ``aud`` claim.
            allowed_algorithms: Allowed asymmetric signing algorithms.
            require_access_token_typ: Require RFC 9068 ``typ: at+jwt`` header.
            reject_id_tokens: Reject OIDC ID tokens on resource-server routes.
            jwks_cache_ttl_seconds: JWKS cache TTL in seconds.
            jwks_timeout_seconds: HTTP request timeout in seconds.
            roles_claim: Claim name mapped to ``Identity.roles``.
            permissions_claim: Claim name mapped to ``Identity.permissions``.
            tenant_claim: Claim name mapped to ``Identity.tenant_id``.
            leeway_seconds: Clock-skew leeway in seconds.
            http_client: Optional sync HTTP client for discovery fetch.
            jwk_client: Optional custom JWK client override.

        Returns:
            Configured ``JwksOidcSecurityAdapter`` bound to discovered ``issuer``
            and ``jwks_uri``.
        """
        doc = discover_oidc_configuration(
            discovery_url, timeout=jwks_timeout_seconds, http_client=http_client
        )
        return cls(
            jwks_uri=doc.jwks_uri,
            issuer=doc.issuer,
            audience=audience,
            allowed_algorithms=allowed_algorithms,
            require_access_token_typ=require_access_token_typ,
            reject_id_tokens=reject_id_tokens,
            jwks_cache_ttl_seconds=jwks_cache_ttl_seconds,
            jwks_timeout_seconds=jwks_timeout_seconds,
            roles_claim=roles_claim,
            permissions_claim=permissions_claim,
            tenant_claim=tenant_claim,
            leeway_seconds=leeway_seconds,
            jwk_client=jwk_client,
        )

    @classmethod
    async def from_discovery_async(
        cls,
        discovery_url: str,
        *,
        audience: str | tuple[str, ...],
        allowed_algorithms: tuple[str, ...] = DEFAULT_ASYMMETRIC_OIDC_ALGORITHMS,
        require_access_token_typ: bool = False,
        reject_id_tokens: bool = True,
        jwks_cache_ttl_seconds: int = 300,
        jwks_timeout_seconds: float = 5.0,
        roles_claim: str = "roles",
        permissions_claim: str = "permissions",
        tenant_claim: str = "tenant_id",
        leeway_seconds: int = 30,
        http_client: Any | None = None,
        jwk_client: Any | None = None,
    ) -> JwksOidcSecurityAdapter:
        """Construct adapter asynchronously from ``/.well-known/openid-configuration``.

        Args:
            discovery_url: Issuer URL or explicit OIDC discovery endpoint URL.
            audience: Expected resource-server ``aud`` claim.
            allowed_algorithms: Allowed asymmetric signing algorithms.
            require_access_token_typ: Require RFC 9068 ``typ: at+jwt`` header.
            reject_id_tokens: Reject OIDC ID tokens on resource-server routes.
            jwks_cache_ttl_seconds: JWKS cache TTL in seconds.
            jwks_timeout_seconds: HTTP request timeout in seconds.
            roles_claim: Claim name mapped to ``Identity.roles``.
            permissions_claim: Claim name mapped to ``Identity.permissions``.
            tenant_claim: Claim name mapped to ``Identity.tenant_id``.
            leeway_seconds: Clock-skew leeway in seconds.
            http_client: Optional async HTTP client for discovery fetch.
            jwk_client: Optional custom JWK client override.

        Returns:
            Configured ``JwksOidcSecurityAdapter`` bound to discovered ``issuer``
            and ``jwks_uri``.
        """
        doc = await discover_oidc_configuration_async(
            discovery_url, timeout=jwks_timeout_seconds, http_client=http_client
        )
        return cls(
            jwks_uri=doc.jwks_uri,
            issuer=doc.issuer,
            audience=audience,
            allowed_algorithms=allowed_algorithms,
            require_access_token_typ=require_access_token_typ,
            reject_id_tokens=reject_id_tokens,
            jwks_cache_ttl_seconds=jwks_cache_ttl_seconds,
            jwks_timeout_seconds=jwks_timeout_seconds,
            roles_claim=roles_claim,
            permissions_claim=permissions_claim,
            tenant_claim=tenant_claim,
            leeway_seconds=leeway_seconds,
            jwk_client=jwk_client,
        )

    def create_token(
        self,
        identity: Identity,
        *,
        ttl: Any = None,
    ) -> str:
        """Raise ``AuthError`` because OIDC resource-server adapters never mint tokens.

        Args:
            identity: Ignored identity object.
            ttl: Ignored lifetime override.

        Raises:
            AuthError: Always raised; tokens are minted only by the upstream OIDC IdP.
        """
        msg = (
            "JwksOidcSecurityAdapter is verification-only; OIDC tokens must be "
            "issued by the upstream identity provider."
        )
        raise AuthError(msg)

    def _validate_header(self, token: str) -> dict[str, Any]:
        """Inspect JWT header and reject forbidden or non-allowlisted algorithms."""
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(f"Malformed JWT header: {exc}") from exc

        alg = header.get("alg")
        if not isinstance(alg, str) or not alg.strip():
            raise InvalidTokenError("JWT header missing 'alg' algorithm identifier.")

        lowered = alg.strip().casefold()
        if lowered == "none" or lowered.startswith("hs"):
            raise InvalidTokenError(
                f"JWT algorithm '{alg}' is forbidden for OIDC verification."
            )
        if alg not in self._policy.allowed_algorithms:
            raise InvalidTokenError(
                f"JWT algorithm '{alg}' is not permitted by OIDC policy."
            )
        return dict(header)

    def _get_signing_key(self, token: str) -> Any:
        """Resolve public signing key from JWKS with one cache-refresh retry on rotation."""
        try:
            return self._jwk_client.get_signing_key_from_jwt(token)
        except jwt.PyJWKClientError as first_exc:
            get_jwk_set = getattr(self._jwk_client, "get_jwk_set", None)
            if callable(get_jwk_set):
                try:
                    get_jwk_set(refresh=True)
                except jwt.PyJWKClientError as refresh_exc:
                    raise InvalidTokenError(
                        f"Failed to refresh OIDC JWKS key set: {refresh_exc}"
                    ) from refresh_exc
            elif not self._custom_jwk_client:
                self._jwk_client = self._build_jwk_client()

            try:
                return self._jwk_client.get_signing_key_from_jwt(token)
            except jwt.PyJWKClientError as retry_exc:
                raise InvalidTokenError(
                    f"Unable to resolve OIDC signing key: {retry_exc}"
                ) from first_exc

    def _decode_and_verify_claims(
        self,
        token: str,
        *,
        audience: str | tuple[str, ...],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Verify cryptographic signature, issuer, audience, expiration, and sub."""
        if not token:
            raise InvalidTokenError("Token string cannot be empty.")

        header = self._validate_header(token)
        signing_key = self._get_signing_key(token)

        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=list(self._policy.allowed_algorithms),
                issuer=self._policy.issuer,
                audience=audience,
                leeway=self._policy.leeway_seconds,
                options={
                    "require": ["exp", "sub", "iss", "aud"],
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "verify_signature": True,
                },
            )
        except jwt.ExpiredSignatureError as exc:
            raise TokenExpiredError(f"OIDC JWT token expired: {exc}") from exc
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(f"Invalid OIDC JWT token: {exc}") from exc
        except Exception as exc:
            raise AuthError(f"OIDC token verification failed: {exc}") from exc

        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub.strip():
            raise InvalidTokenError("OIDC JWT token missing required 'sub' claim.")
        return header, claims

    def _enforce_access_token_semantics(
        self,
        header: Mapping[str, Any],
        claims: Mapping[str, Any],
    ) -> None:
        """Enforce access-token vs. OIDC ID-token separation rules."""
        typ = str(header.get("typ") or "").strip().casefold()
        if self._policy.reject_id_tokens:
            if typ in {"id+jwt", "application/id+jwt"}:
                raise InvalidTokenError(
                    "OIDC ID token ('typ=id+jwt') cannot be used as a bearer access token."
                )
            if str(claims.get("token_use") or "").strip().casefold() == "id":
                raise InvalidTokenError(
                    "OIDC ID token ('token_use=id') cannot be used as a bearer access token."
                )
            for marker in ("nonce", "at_hash", "c_hash"):
                if marker in claims and claims[marker] is not None:
                    raise InvalidTokenError(
                        f"OIDC ID token carrying '{marker}' claim cannot be used as a bearer access token."
                    )

        if self._policy.require_access_token_typ and typ not in {
            "at+jwt",
            "application/at+jwt",
        }:
            raise InvalidTokenError(
                "Bearer access token missing required RFC 9068 'typ=at+jwt' header."
            )

    def verify_token(self, token: str) -> Identity:
        """Verify an OIDC bearer access token and reconstruct an ``Identity``.

        Args:
            token: Signed asymmetric JWT bearer access token.

        Returns:
            Verified ``Identity`` populated with ``sub``, roles, permissions,
            tenant ID, and raw claims.

        Raises:
            TokenExpiredError: If the token has expired past allowed leeway.
            InvalidTokenError: If signature, ``alg``, ``iss``, ``aud``, ``sub``,
                or access-token type enforcement fails.
            AuthError: If unexpected verification errors occur.
        """
        header, claims = self._decode_and_verify_claims(
            token, audience=self._policy.audience
        )
        self._enforce_access_token_semantics(header, claims)

        roles = _extract_str_collection(claims.get(self._policy.roles_claim))
        permissions = _extract_str_collection(
            claims.get(self._policy.permissions_claim)
        )
        tenant_val = claims.get(self._policy.tenant_claim)
        tenant_id = (
            str(tenant_val)
            if tenant_val is not None and str(tenant_val).strip()
            else None
        )

        return Identity(
            user_id=str(claims["sub"]),
            roles=roles,
            permissions=permissions,
            tenant_id=tenant_id,
            claims=claims,
            is_authenticated=True,
        )

    def verify_id_token(
        self,
        id_token: str,
        *,
        expected_nonce: str | None = None,
        client_id: str | None = None,
    ) -> dict[str, Any]:
        """Verify an OpenID Connect ID token and validate its ``nonce`` claim.

        Args:
            id_token: Raw signed OIDC ID token string.
            expected_nonce: Ephemeral nonce issued on the authorization request.
            client_id: Optional OAuth2 ``client_id`` expected in ``aud`` (defaults
                to ``self._policy.audience``).

        Returns:
            Decoded and verified ID token claims dictionary.

        Raises:
            TokenExpiredError: If the ID token has expired.
            InvalidTokenError: If signature, issuer, audience, or nonce fails.
        """
        target_aud: str | tuple[str, ...] = client_id or self._policy.audience
        _, claims = self._decode_and_verify_claims(id_token, audience=target_aud)
        if expected_nonce is not None:
            actual_nonce = claims.get("nonce")
            if not isinstance(actual_nonce, str) or not hmac.compare_digest(
                actual_nonce, expected_nonce
            ):
                raise InvalidTokenError(
                    "OIDC ID token 'nonce' claim does not match expected request nonce."
                )
        return claims


__all__ = [
    "discover_oidc_configuration",
    "discover_oidc_configuration_async",
    "JwksOidcSecurityAdapter",
]
