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


def test_parse_github_url_variants() -> None:
    """Verify _parse_github_url handles SSH SCP, HTTPS, and userinfo formats."""
    from hexastack_tools.adapters.github.client import _parse_github_url

    # SSH SCP format
    assert _parse_github_url("git@github.com:TheTrueSCU/hexastack.git") == (
        "TheTrueSCU",
        "hexastack",
    )
    assert _parse_github_url("git@github.com:Owner/Repo") == ("Owner", "Repo")

    # HTTPS format
    assert _parse_github_url("https://github.com/TheTrueSCU/hexastack.git") == (
        "TheTrueSCU",
        "hexastack",
    )
    assert _parse_github_url("https://github.com/TheTrueSCU/hexastack") == (
        "TheTrueSCU",
        "hexastack",
    )
    assert _parse_github_url("https://github.com/TheTrueSCU/hexastack.git/") == (
        "TheTrueSCU",
        "hexastack",
    )
    assert _parse_github_url("git@github.com:TheTrueSCU/hexastack.git/") == (
        "TheTrueSCU",
        "hexastack",
    )

    # HTTPS with userinfo
    assert (
        _parse_github_url(
            "https://user:token@github.com/TheTrueSCU/hexastack.git"  # pragma: allowlist secret
        )
        == (
            "TheTrueSCU",
            "hexastack",
        )
    )

    # Non-GitHub host returns None
    assert _parse_github_url("git@gitlab.com:TheTrueSCU/hexastack.git") is None
    assert _parse_github_url("https://gitlab.com/TheTrueSCU/hexastack.git") is None
