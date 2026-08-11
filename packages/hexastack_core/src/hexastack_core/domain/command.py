from pydantic import BaseModel, ConfigDict


class Command(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
