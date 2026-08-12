import types

from hexastack_mcp.infra.autodiscovery import (
    autodiscover_mcp_elements,
)
from hexastack_mcp.infra.decorators import (
    mcp_prompt,
    mcp_resource,
    mcp_tool,
)
from hexastack_mcp.infra.registries.server import McpServerRegistry


def test_autodiscover_mcp_elements():
    mod = types.ModuleType("dummy_mcp_mod")

    @mcp_tool(name="discovered_tool")
    def tool_fn() -> str:
        return "tool"

    @mcp_resource(uri="discovered://res", name="res")
    def res_fn() -> str:
        return "res"

    @mcp_prompt(name="prompt")
    def prompt_fn() -> str:
        return "prompt"

    setattr(mod, "tool_fn", tool_fn)  # noqa: B010
    setattr(mod, "res_fn", res_fn)  # noqa: B010
    setattr(mod, "prompt_fn", prompt_fn)  # noqa: B010

    custom_reg = McpServerRegistry()
    autodiscover_mcp_elements([mod], custom_reg)

    assert len(custom_reg._tools) == 1
    assert custom_reg._tools[0].name == "discovered_tool"
    assert len(custom_reg._resources) == 1
    assert custom_reg._resources[0].name == "res"
    assert len(custom_reg._prompts) == 1
    assert custom_reg._prompts[0].name == "prompt"
