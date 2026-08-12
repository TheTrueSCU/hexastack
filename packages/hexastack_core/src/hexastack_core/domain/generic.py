from pydantic import BaseModel, ConfigDict


class Generic(BaseModel):
    """Base immutable Pydantic model for domain commands, events, and queries.

    Notes/Architectural Intent:
        Enforces immutability (frozen=True) and forbids extra undeclared parameters (extra="forbid")
        to guarantee value-object semantics and strict message validation across the stack.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
