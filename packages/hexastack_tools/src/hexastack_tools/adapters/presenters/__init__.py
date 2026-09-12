"""Presenters package export for hexastack_tools."""

from hexastack_tools.adapters.presenters.analysis import (
    JsonAnalysisPresenterAdapter,
    MarkdownAnalysisPresenterAdapter,
    RichAnalysisPresenterAdapter,
    create_analysis_presenter,
)
from hexastack_tools.adapters.presenters.checks import (
    build_checks_table,
    present_checks,
    render_checks_json,
    render_checks_plain,
)
from hexastack_tools.adapters.presenters.common import resolve_output_format
from hexastack_tools.adapters.presenters.dependency import (
    JsonDependencyPresenterAdapter,
    MarkdownDependencyPresenterAdapter,
    RichDependencyPresenterAdapter,
    create_dependency_presenter,
)
from hexastack_tools.adapters.presenters.generators import (
    JsonGeneratorPresenterAdapter,
    MarkdownGeneratorPresenterAdapter,
    RichGeneratorPresenterAdapter,
    create_generator_presenter,
)
from hexastack_tools.adapters.presenters.github import (
    JsonGitHubPresenterAdapter,
    MarkdownGitHubPresenterAdapter,
    RichGitHubPresenterAdapter,
    create_github_presenter,
)
from hexastack_tools.adapters.presenters.governance import (
    JsonGovernancePresenterAdapter,
    MarkdownGovernancePresenterAdapter,
    RichGovernancePresenterAdapter,
    create_governance_presenter,
)
from hexastack_tools.adapters.presenters.pr import (
    present_pr_summary,
    render_pr_summary_json,
    render_pr_summary_plain,
    render_pr_summary_rich,
)
from hexastack_tools.adapters.presenters.pypi import (
    JsonPyPiPresenterAdapter,
    MarkdownPyPiPresenterAdapter,
    RichPyPiPresenterAdapter,
    create_pypi_presenter,
)
from hexastack_tools.adapters.presenters.refactoring import (
    JsonRefactoringPresenterAdapter,
    MarkdownRefactoringPresenterAdapter,
    RichRefactoringPresenterAdapter,
    create_refactoring_presenter,
)
from hexastack_tools.adapters.presenters.repo import (
    build_repo_status_table,
    present_repo_status,
    render_repo_status_json,
    render_repo_status_plain,
)
from hexastack_tools.adapters.presenters.security import (
    build_security_comments_table,
    present_security_comments,
    render_security_comments_json,
    render_security_comments_plain,
)
from hexastack_tools.adapters.presenters.testing import (
    JsonTestingPresenterAdapter,
    MarkdownTestingPresenterAdapter,
    RichTestingPresenterAdapter,
    create_testing_presenter,
)

__all__ = [
    "build_checks_table",
    "build_repo_status_table",
    "build_security_comments_table",
    "create_analysis_presenter",
    "create_dependency_presenter",
    "create_generator_presenter",
    "create_github_presenter",
    "create_governance_presenter",
    "create_pypi_presenter",
    "create_refactoring_presenter",
    "create_testing_presenter",
    "JsonAnalysisPresenterAdapter",
    "JsonDependencyPresenterAdapter",
    "JsonGeneratorPresenterAdapter",
    "JsonGitHubPresenterAdapter",
    "JsonGovernancePresenterAdapter",
    "JsonPyPiPresenterAdapter",
    "JsonRefactoringPresenterAdapter",
    "JsonTestingPresenterAdapter",
    "MarkdownAnalysisPresenterAdapter",
    "MarkdownDependencyPresenterAdapter",
    "MarkdownGeneratorPresenterAdapter",
    "MarkdownGitHubPresenterAdapter",
    "MarkdownGovernancePresenterAdapter",
    "MarkdownPyPiPresenterAdapter",
    "MarkdownRefactoringPresenterAdapter",
    "MarkdownTestingPresenterAdapter",
    "present_checks",
    "present_pr_summary",
    "present_repo_status",
    "present_security_comments",
    "render_checks_json",
    "render_checks_plain",
    "render_pr_summary_json",
    "render_pr_summary_plain",
    "render_pr_summary_rich",
    "render_repo_status_json",
    "render_repo_status_plain",
    "render_security_comments_json",
    "render_security_comments_plain",
    "resolve_output_format",
    "RichAnalysisPresenterAdapter",
    "RichDependencyPresenterAdapter",
    "RichGeneratorPresenterAdapter",
    "RichGitHubPresenterAdapter",
    "RichGovernancePresenterAdapter",
    "RichPyPiPresenterAdapter",
    "RichRefactoringPresenterAdapter",
    "RichTestingPresenterAdapter",
]
