import types

import pytest
from hexastack_mcp.infra.autodiscovery import (
    autodiscover_mcp_elements,
)
from hexastack_mcp.infra.decorators import (
    get_mcp_registry,
    mcp_prompt,
    mcp_resource,
    mcp_tool,
)
from hexastack_mcp.infra.registries.server import McpServerRegistry


@pytest.fixture(autouse=True)
def clean_registry():
    reg = get_mcp_registry()
    reg.clear()
    yield
    reg.clear()


def test_autodiscover_mcp_elements():
    mod = types.ModuleType("dummy_mcp_mod")

    @mcp_tool(name="dummy_tool")
    def tool_fn(x: int) -> int:
        return x * 2

    @mcp_resource(uri="hexastack://dummy", name="dummy_res")
    def res_fn() -> str:
        return "dummy content"

    @mcp_prompt(name="dummy_prompt")
    def prompt_fn(topic: str) -> str:
        return f"Prompt on {topic}"

    setattr(mod, "tool_fn", tool_fn)  # noqa: B010
    setattr(mod, "res_fn", res_fn)  # noqa: B010
    setattr(mod, "prompt_fn", prompt_fn)  # noqa: B010

    custom_reg = McpServerRegistry()
    autodiscover_mcp_elements([mod], custom_reg)

    assert len(custom_reg._tools) == 1
    assert custom_reg._tools[0].name == "dummy_tool"

    assert len(custom_reg._resources) == 1
    assert custom_reg._resources[0].uri == "hexastack://dummy"

    assert len(custom_reg._prompts) == 1
    assert custom_reg._prompts[0].name == "dummy_prompt"
