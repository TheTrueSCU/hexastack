from hexastack_core.infra.decorators import (
    ConfigMetadata,
    ExceptionMetadata,
    config_section,
    exception_handler,
)
from pydantic import BaseModel


class SampleCustomError(Exception):
    pass


class SampleSectionConfig(BaseModel):
    enabled: bool = True


def test_config_section_decorator():
    @config_section("app.sample")
    class Config(BaseModel):
        timeout: int = 30

    meta = getattr(Config, "__hexastack_handler__", None)
    assert isinstance(meta, ConfigMetadata)
    assert meta.section_name == "app.sample"


def test_exception_handler_decorator():
    @exception_handler(SampleCustomError)
    def handle_error(exc: SampleCustomError) -> dict[str, str]:
        return {"error": str(exc)}

    meta = getattr(handle_error, "__hexastack_handler__", None)
    assert isinstance(meta, ExceptionMetadata)
    assert meta.target_cls == SampleCustomError
