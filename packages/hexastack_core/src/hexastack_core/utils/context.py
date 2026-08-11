from contextvars import ContextVar
from dataclasses import dataclass, field


@dataclass(frozen=True)
class UserContext:
    user_id: str
    roles: list[str] = field(default_factory=list)
    tenant_id: str | None = None

correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")
user_ctx: ContextVar[UserContext | None] = ContextVar("user", default=None)
