"""Unit tests for GitHub HTTP client adapter."""

from hexastack_tools.adapters.github.client import (
    GitHubHttpAdapter,
    get_github_token,
)


def test_get_github_token() -> None:
    """Verify token resolution callable executes safely."""
    token = get_github_token()
    # May be string or None depending on environment
    assert token is None or isinstance(token, str)


def test_github_http_adapter_init() -> None:
    """Verify adapter initialization and context manager."""
    with GitHubHttpAdapter(token="dummy", owner="TestOwner", repo="TestRepo") as client:
        assert client.owner == "TestOwner"
        assert client.repo == "TestRepo"
        assert client.token == "dummy"
