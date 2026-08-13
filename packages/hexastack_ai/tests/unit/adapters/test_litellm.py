from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hexastack_ai.adapters.litellm import LiteLlmAdapter
from hexastack_ai.domain.exceptions import LlmProviderError
from hexastack_ai.infra.config import HexastackAiConfig
from pydantic import BaseModel


class SummarySchema(BaseModel):
    title: str
    score: int


def test_litellm_adapter_generate_text():
    mock_choice = MagicMock()
    mock_choice.message.content = "Mocked AI Response"
    mock_response = MagicMock(choices=[mock_choice])

    with patch("litellm.completion", return_value=mock_response) as mock_comp:
        config = HexastackAiConfig(model="gpt-4o", temperature=0.5)
        adapter = LiteLlmAdapter(config=config)

        res = adapter.generate_text("Hello AI", system_prompt="Be concise")
        assert res == "Mocked AI Response"
        mock_comp.assert_called_once()


@pytest.mark.anyio
async def test_litellm_adapter_generate_text_async():
    mock_choice = MagicMock()
    mock_choice.message.content = "Async AI Response"
    mock_response = MagicMock(choices=[mock_choice])

    with patch(
        "litellm.acompletion", new_callable=AsyncMock, return_value=mock_response
    ) as mock_acomp:
        config = HexastackAiConfig(model="gpt-4o")
        adapter = LiteLlmAdapter(config=config)

        res = await adapter.generate_text_async("Hello Async")
        assert res == "Async AI Response"
        mock_acomp.assert_called_once()


def test_litellm_adapter_generate_structured():
    expected = SummarySchema(title="Report", score=95)
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = expected

    with patch("instructor.from_litellm", return_value=mock_client):
        adapter = LiteLlmAdapter()
        res = adapter.generate_structured("Analyze this", SummarySchema)
        assert res == expected
        assert res.title == "Report"
        assert res.score == 95


def test_litellm_adapter_error_handling():
    with patch("litellm.completion", side_effect=RuntimeError("API down")):
        adapter = LiteLlmAdapter()
        with pytest.raises(LlmProviderError) as exc_info:
            adapter.generate_text("Fail please")
        assert "API down" in str(exc_info.value)
