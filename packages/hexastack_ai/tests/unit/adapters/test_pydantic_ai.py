from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai import Agent

from hexastack_ai.adapters.pydantic_ai import PydanticAiAgentAdapter
from hexastack_ai.domain.exceptions import AgentExecutionError


@pytest.mark.anyio
async def test_pydantic_ai_agent_adapter_run_async():
    mock_agent = MagicMock(spec=Agent)
    mock_result = MagicMock()
    mock_result.output = "Agent completed task"
    mock_agent.run = AsyncMock(return_value=mock_result)

    adapter = PydanticAiAgentAdapter(agent=mock_agent)
    assert adapter.agent is mock_agent

    data = await adapter.run("Do something")
    assert data == "Agent completed task"


def test_pydantic_ai_agent_adapter_run_sync():
    mock_agent = MagicMock(spec=Agent)
    mock_result = MagicMock()
    mock_result.output = "Sync result"
    mock_agent.run_sync.return_value = mock_result

    adapter = PydanticAiAgentAdapter(agent=mock_agent)
    data = adapter.run_sync("Sync prompt")
    assert data == "Sync result"


def test_pydantic_ai_agent_adapter_error_translation():
    mock_agent = MagicMock(spec=Agent)
    mock_agent.run_sync.side_effect = RuntimeError("Turn limit exceeded")

    adapter = PydanticAiAgentAdapter(agent=mock_agent)
    with pytest.raises(AgentExecutionError) as exc_info:
        adapter.run_sync("Will fail")
    assert "Turn limit exceeded" in str(exc_info.value)
