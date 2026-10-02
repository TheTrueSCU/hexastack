"""Progressive Tutorial demo step helpers decomposed by chapter.

Notes/Architectural Intent:
    Exports granular sub-steps and complete orchestrators for Tutorial Chapters 1 through 7.
"""

from tests.e2e.tutorials.helpers.ch01 import (
    step_ch01_1_scaffold_project,
    step_ch01_2_inspect_layout,
    step_ch01_scaffold_minimal,
)
from tests.e2e.tutorials.helpers.ch02 import (
    step_ch02_1_scaffold_sqlite_service,
    step_ch02_2_inspect_db_commands,
    step_ch02_configure_sqlite,
)
from tests.e2e.tutorials.helpers.ch03 import (
    step_ch03_1_inspect_registry_auth,
    step_ch03_configure_jwt_auth,
)
from tests.e2e.tutorials.helpers.ch04 import (
    step_ch04_1_inspect_outbox_relay,
    step_ch04_configure_events_outbox,
)
from tests.e2e.tutorials.helpers.ch05 import (
    step_ch05_1_list_mcp_tools,
    step_ch05_2_generate_mcp_config,
    step_ch05_configure_ai_mcp,
)
from tests.e2e.tutorials.helpers.ch06 import (
    step_ch06_1_inspect_ui_command,
    step_ch06_configure_observability,
)
from tests.e2e.tutorials.helpers.ch07 import (
    step_ch07_1_list_grpc_services,
    step_ch07_2_inspect_grpc_compile,
    step_ch07_configure_grpc,
)

__all__ = [
    "step_ch01_1_scaffold_project",
    "step_ch01_2_inspect_layout",
    "step_ch01_scaffold_minimal",
    "step_ch02_1_scaffold_sqlite_service",
    "step_ch02_2_inspect_db_commands",
    "step_ch02_configure_sqlite",
    "step_ch03_1_inspect_registry_auth",
    "step_ch03_configure_jwt_auth",
    "step_ch04_1_inspect_outbox_relay",
    "step_ch04_configure_events_outbox",
    "step_ch05_1_list_mcp_tools",
    "step_ch05_2_generate_mcp_config",
    "step_ch05_configure_ai_mcp",
    "step_ch06_1_inspect_ui_command",
    "step_ch06_configure_observability",
    "step_ch07_1_list_grpc_services",
    "step_ch07_2_inspect_grpc_compile",
    "step_ch07_configure_grpc",
]
