import inspect
from typing import Any

from pydantic import BaseModel

from hexastack_ai.domain.config import HexastackAiConfig
from hexastack_ai.domain.exceptions import (
    LlmProviderError,
    StructuredOutputParsingError,
)
from hexastack_core.ports.ai import LlmProviderPort


class LiteLlmAdapter(LlmProviderPort):
    """LiteLLM and Instructor adapter implementing LlmProviderPort.

    Notes/Architectural Intent:
        Wraps LiteLLM to provide vendor-agnostic LLM calls across 100+ providers
        (OpenAI, Claude, Gemini, Ollama, Bedrock) while leveraging Instructor
        for self-correcting structured output validation.
    """

    def __init__(self, config: HexastackAiConfig | None = None) -> None:
        """Initialize LiteLlmAdapter with configuration.

        Args:
            config: HexastackAiConfig instance.
        """
        self._config = config or HexastackAiConfig()

    @property
    def _resolved_model(self) -> str:
        """Resolve full model identifier ensuring provider prefix like 'gemini/' is handled."""
        model = self._config.model
        provider = self._config.provider.lower()
        if provider == "gemini" and not model.startswith("gemini/"):
            return f"gemini/{model}"
        if provider == "anthropic" and not model.startswith("anthropic/"):
            return f"anthropic/{model}"
        if provider == "ollama" and not model.startswith("ollama/"):
            return f"ollama/{model}"
        return model

    def generate_structured[T: BaseModel](
        self, prompt: str, response_schema: type[T]
    ) -> T:
        """Generate structured Pydantic output using Instructor over LiteLLM.

        Args:
            prompt: The user prompt text.
            response_schema: Target Pydantic model class.

        Returns:
            Validated instance of response_schema.

        Raises:
            StructuredOutputParsingError: If schema validation fails.
            LlmProviderError: If API call fails.
        """
        import instructor
        import litellm
        from instructor.core import InstructorRetryException

        client = instructor.from_litellm(litellm.completion)

        kwargs: dict[str, Any] = {
            "model": self._resolved_model,
            "messages": [{"role": "user", "content": prompt}],
            "response_model": response_schema,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
        }
        if self._config.api_key:
            kwargs["api_key"] = self._config.api_key
        if self._config.litellm.api_base:
            kwargs["api_base"] = self._config.litellm.api_base

        try:
            return client.chat.completions.create(**kwargs)
        except InstructorRetryException as exc:
            raise StructuredOutputParsingError(
                f"Failed to generate structured {response_schema.__name__}: {exc}"
            ) from exc
        except Exception as exc:
            raise LlmProviderError(
                str(exc),
                provider=self._config.provider,
                model=self._config.model,
            ) from exc

    async def generate_structured_async[T: BaseModel](
        self, prompt: str, response_schema: type[T]
    ) -> T:
        """Asynchronously generate structured Pydantic output using Instructor over LiteLLM."""
        import instructor
        import litellm
        from instructor.core import InstructorRetryException

        client = instructor.from_litellm(litellm.acompletion)

        kwargs: dict[str, Any] = {
            "model": self._resolved_model,
            "messages": [{"role": "user", "content": prompt}],
            "response_model": response_schema,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
        }
        if self._config.api_key:
            kwargs["api_key"] = self._config.api_key
        if self._config.litellm.api_base:
            kwargs["api_base"] = self._config.litellm.api_base

        try:
            raw_result: Any = client.chat.completions.create(**kwargs)
            if inspect.isawaitable(raw_result):
                return await raw_result
            return raw_result
        except InstructorRetryException as exc:
            raise StructuredOutputParsingError(
                f"Failed to generate structured {response_schema.__name__}: {exc}"
            ) from exc
        except Exception as exc:
            raise LlmProviderError(
                str(exc),
                provider=self._config.provider,
                model=self._config.model,
            ) from exc

    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        """Generate unstructured text from a prompt via LiteLLM.

        Args:
            prompt: The user prompt text.
            system_prompt: Optional system instruction prompt.

        Returns:
            Generated response text.

        Raises:
            LlmProviderError: If the upstream provider request fails.
        """
        import litellm

        messages: list[dict[str, str]] = []
        if system_prompt or self._config.agent.system_prompt:
            sys = system_prompt or self._config.agent.system_prompt
            if sys:
                messages.append({"role": "system", "content": sys})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self._resolved_model,
            "messages": messages,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "drop_params": self._config.litellm.drop_params,
            "num_retries": self._config.litellm.num_retries,
            "timeout": self._config.litellm.timeout,
        }
        if self._config.api_key:
            kwargs["api_key"] = self._config.api_key
        if self._config.litellm.api_base:
            kwargs["api_base"] = self._config.litellm.api_base

        try:
            response = litellm.completion(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LlmProviderError(
                str(exc),
                provider=self._config.provider,
                model=self._config.model,
            ) from exc

    async def generate_text_async(
        self, prompt: str, system_prompt: str | None = None
    ) -> str:
        """Asynchronously generate unstructured text from a prompt via LiteLLM.

        Args:
            prompt: The user prompt text.
            system_prompt: Optional system instruction prompt.

        Returns:
            Generated response text.

        Raises:
            LlmProviderError: If the upstream provider request fails.
        """
        import litellm

        messages: list[dict[str, str]] = []
        if system_prompt or self._config.agent.system_prompt:
            sys = system_prompt or self._config.agent.system_prompt
            if sys:
                messages.append({"role": "system", "content": sys})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": self._resolved_model,
            "messages": messages,
            "temperature": self._config.temperature,
            "max_tokens": self._config.max_tokens,
            "drop_params": self._config.litellm.drop_params,
            "num_retries": self._config.litellm.num_retries,
            "timeout": self._config.litellm.timeout,
        }
        if self._config.api_key:
            kwargs["api_key"] = self._config.api_key
        if self._config.litellm.api_base:
            kwargs["api_base"] = self._config.litellm.api_base

        try:
            response = await litellm.acompletion(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LlmProviderError(
                str(exc),
                provider=self._config.provider,
                model=self._config.model,
            ) from exc


__all__ = [
    "LiteLlmAdapter",
]
