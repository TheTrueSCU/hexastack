import re
from typing import Any

from pydantic import BaseModel

_DEFAULT_MASKED_KEYS = {
    "access_token",
    "api_key",
    "authorization",
    "bearer",
    "card_number",
    "credit_card",
    "cvv",
    "password",
    "private_key",
    "refresh_token",
    "secret",
    "ssn",
    "token",
}

_DEFAULT_PATTERNS = [
    r"Bearer\s+[A-Za-z0-9\-\._~\+\/]+=*",
    r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
]


class Sanitizer:
    """Log and data sanitizer for masking PII, credentials, and sensitive tokens.

    Notes/Architectural Intent:
        Scans nested dictionaries, lists, strings, Pydantic models, and stack traces,
        replacing sensitive key values and matching regex patterns with redaction placeholders.
    """

    def __init__(
        self,
        masked_keys: list[str] | set[str] | None = None,
        mask_replacement: str = "***REDACTED***",
        regex_patterns: list[str] | None = None,
    ) -> None:
        """Initialize Sanitizer with key names, replacement placeholder, and regex patterns.

        Args:
            masked_keys: Optional list/set of sensitive key names to mask (case-insensitive).
            mask_replacement: String placeholder to substitute masked values with.
            regex_patterns: Optional list of regex string patterns for inline string scrubbing.
        """
        self._masked_keys = {
            k.lower()
            for k in (masked_keys if masked_keys is not None else _DEFAULT_MASKED_KEYS)
        }
        self._mask_replacement = mask_replacement
        patterns = regex_patterns if regex_patterns is not None else _DEFAULT_PATTERNS
        self._compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

    def sanitize(self, value: Any) -> Any:
        """Recursively sanitize any Python data structure, string, or model.

        Args:
            value: The data object to sanitize.

        Returns:
            The sanitized data structure with sensitive items masked.

        Raises:
            None.
        """
        if isinstance(value, dict):
            return self.sanitize_dict(value)
        if isinstance(value, list):
            return self.sanitize_list(value)
        if isinstance(value, tuple):
            return tuple(self.sanitize_list(list(value)))
        if isinstance(value, set):
            return {self.sanitize(item) for item in value}
        if isinstance(value, BaseModel):
            return self.sanitize_dict(value.model_dump())
        if isinstance(value, str):
            return self.sanitize_string(value)
        return value

    def sanitize_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively sanitize a dictionary, masking matching keys.

        Args:
            data: The dictionary to sanitize.

        Returns:
            A new dictionary with masked values for sensitive keys.

        Raises:
            None.
        """
        sanitized: dict[str, Any] = {}
        for k, v in data.items():
            if str(k).lower() in self._masked_keys:
                sanitized[k] = self._mask_replacement
            elif isinstance(v, dict):
                sanitized[k] = self.sanitize_dict(v)
            elif isinstance(v, list):
                sanitized[k] = self.sanitize_list(v)
            elif isinstance(v, BaseModel):
                sanitized[k] = self.sanitize_dict(v.model_dump())
            elif isinstance(v, str):
                sanitized[k] = self.sanitize_string(v)
            else:
                sanitized[k] = v
        return sanitized

    def sanitize_list(self, items: list[Any]) -> list[Any]:
        """Recursively sanitize a list of items.

        Args:
            items: List of data elements.

        Returns:
            A new list with sanitized elements.

        Raises:
            None.
        """
        return [self.sanitize(item) for item in items]

    def sanitize_string(self, text: str) -> str:
        """Sanitize an inline string by scrubbing regex pattern matches.

        Args:
            text: The string to scrub.

        Returns:
            Scrubbed string with pattern matches replaced.

        Raises:
            None.
        """
        result = text
        for pattern in self._compiled_patterns:
            result = pattern.sub(self._mask_replacement, result)
        return result

    def sanitize_traceback(self, tb_text: str) -> str:
        """Sanitize a formatted traceback or exception string.

        Args:
            tb_text: Formatted traceback string.

        Returns:
            Scrubbed traceback string.

        Raises:
            None.
        """
        return self.sanitize_string(tb_text)
