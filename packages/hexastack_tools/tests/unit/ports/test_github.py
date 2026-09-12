"""Unit tests for hexastack_tools ports."""

from hexastack_tools.ports.github import GitHubApiPort, GitHubPresenterPort


class DummyGitHubAdapter:
    def get_repo_status(self, owner=None, repo=None):
        pass

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

    def get_failed_run_logs(self, run_id):
        pass

    def get_workflow_runs(self, branch=None, limit=5):
        pass


class DummyGitHubPresenter(GitHubPresenterPort):
    def present_pr_summary(self, report):
        return 0

    def present_checks(self, report):
        return 0

    def present_repo_status(self, status):
        return 0

    def present_security_comments(self, report):
        return 0

    def present_code_scanning(self, report):
        return 0


def test_github_api_port_runtime_checkable() -> None:
    """Verify GitHubApiPort protocol runtime checkability."""
    adapter = DummyGitHubAdapter()
    assert isinstance(adapter, GitHubApiPort)


def test_github_presenter_port_instantiation() -> None:
    """Verify GitHubPresenterPort abstract interface contracts."""
    presenter = DummyGitHubPresenter()
    assert isinstance(presenter, GitHubPresenterPort)
