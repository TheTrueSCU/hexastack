import pytest
from pydantic import ValidationError

from hexastack_core.domain.generic import Generic


class SampleGeneric(Generic):
    name: str
    value: int = 0


def test_generic_forbids_extra_fields():
    with pytest.raises(ValidationError):
        SampleGeneric.model_validate({"name": "test", "extra_field": "forbidden"})


def test_generic_immutability():
    obj = SampleGeneric(name="test", value=10)
    assert obj.name == "test"
    assert obj.value == 10

    with pytest.raises(ValidationError):
        setattr(obj, "name", "new_name")  # noqa: B010
