from typing import Self

from pydantic import BaseModel


class Result[T](BaseModel):
    """Generic wrapper representing the success or failure outcome of an operation.

    Notes/Architectural Intent:
        Standardizes return values across domain and infrastructure boundaries without
        relying on exception throwing for expected failure modes.
    """

    success: bool
    data: T | None = None
    error_code: str | None = None
    message: str | None = None

    @classmethod
    def error(cls, code: str, message: str) -> Self:
        """Construct a failure Result container.

        Args:
            code: Machine-readable error code string.
            message: Human-readable error description string.

        Returns:
            An instance of Result representing operation failure.

        Raises:
            None.
        """
        return cls(success=False, error_code=code, message=message)

    @classmethod
    def ok(cls, data: T) -> Self:
        """Construct a successful Result container.

        Args:
            data: Payload returned by the successful operation.

        Returns:
            An instance of Result representing operation success.

        Raises:
            None.
        """
        return cls(success=True, data=data)
