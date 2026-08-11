from typing import Self

from pydantic import BaseModel


class Result[T](BaseModel):
    success: bool
    data: T | None = None
    error_code: str | None = None
    message: str | None = None

    @classmethod
    def error(cls, code: str, message: str) -> Self:
        return cls(success=False, error_code=code, message=message)

    @classmethod
    def ok(cls, data: T) -> Self:
        return cls(success=True, data=data)
