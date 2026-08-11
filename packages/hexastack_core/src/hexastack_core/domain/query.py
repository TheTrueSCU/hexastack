
from pydantic import BaseModel, ConfigDict


class Query[T](BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
