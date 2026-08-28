"""Unit tests for hexastack_tools ports."""

from hexastack_tools.ports.github import GitHubApiPort


class DummyGitHubAdapter:
    def get_pr_summary(self, pr_number: int):
        pass

    def get_check_runs(self, ref: str):
        pass

    def get_review_threads(self, pr_number: int):
        pass

    def get_code_scanning_alerts(self, ref=None, state="open"):
        pass

    def get_single_alert(self, alert_number: int):
        pass


def test_github_api_port_runtime_checkable() -> None:
    """Verify GitHubApiPort protocol runtime checkability."""
    adapter = DummyGitHubAdapter()
    assert isinstance(adapter, GitHubApiPort)
