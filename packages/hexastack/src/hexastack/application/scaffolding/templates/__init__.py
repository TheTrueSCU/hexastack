"""Hexastack scaffolding template renderers."""

from __future__ import annotations

from hexastack.application.scaffolding.templates.adapters import (
    render_buf_yaml,
    render_driven_database,
    render_driving_cli,
    render_driving_graphql,
    render_driving_grpc,
    render_driving_http,
    render_driving_mcp,
    render_mcp_json,
    render_proto_file,
)
from hexastack.application.scaffolding.templates.ci import (
    render_changelog,
    render_github_ci,
    render_github_release,
)
from hexastack.application.scaffolding.templates.config import (
    render_dockerfile,
    render_dockerignore,
    render_importlinter,
    render_precommit,
    render_pyproject_toml,
    render_readme,
)
from hexastack.application.scaffolding.templates.domain import (
    render_domain_commands,
    render_domain_init,
    render_domain_models,
)
from hexastack.application.scaffolding.templates.infra import (
    render_infra_bootstrap,
    render_infra_config,
    render_infra_handlers,
)
from hexastack.application.scaffolding.templates.openssf import (
    render_code_of_conduct_md,
    render_github_scorecard,
    render_governance_md,
    render_security_md,
)
from hexastack.application.scaffolding.templates.ports import (
    render_ports_init,
    render_ports_repositories,
)
from hexastack.application.scaffolding.templates.tests import (
    render_test_conftest,
    render_test_domain,
    render_test_domain_fuzz,
)

__all__ = [
    "render_buf_yaml",
    "render_changelog",
    "render_code_of_conduct_md",
    "render_dockerfile",
    "render_dockerignore",
    "render_domain_commands",
    "render_domain_init",
    "render_domain_models",
    "render_driven_database",
    "render_driving_cli",
    "render_driving_graphql",
    "render_driving_grpc",
    "render_driving_http",
    "render_driving_mcp",
    "render_github_ci",
    "render_github_release",
    "render_github_scorecard",
    "render_governance_md",
    "render_importlinter",
    "render_infra_bootstrap",
    "render_infra_config",
    "render_infra_handlers",
    "render_mcp_json",
    "render_ports_init",
    "render_ports_repositories",
    "render_precommit",
    "render_proto_file",
    "render_pyproject_toml",
    "render_readme",
    "render_security_md",
    "render_test_conftest",
    "render_test_domain",
    "render_test_domain_fuzz",
]
