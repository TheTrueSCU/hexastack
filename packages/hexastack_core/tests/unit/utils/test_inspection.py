from dataclasses import dataclass

from hexastack_core.utils.inspection import (
    extract_dto_fields,
    inspect_model_parameters,
)
from pydantic import BaseModel


@dataclass
class SampleDataclass:
    id: str
    count: int = 1


class SampleModel(BaseModel):
    name: str
    active: bool = True


def test_inspect_model_parameters():
    dc_params = inspect_model_parameters(SampleDataclass)
    assert len(dc_params) == 2
    assert dc_params[0].name == "id"
    assert dc_params[1].name == "count"
    assert dc_params[1].default == 1

    model_params = inspect_model_parameters(SampleModel)
    assert len(model_params) == 2
    assert model_params[0].name == "name"
    assert model_params[1].name == "active"
    assert model_params[1].default is True


def test_extract_dto_fields_from_dict_and_object():
    payload = {"id": "item-1", "count": 5, "extra": "ignored"}
    extracted = extract_dto_fields(payload, SampleDataclass)
    assert extracted["id"] == "item-1"
    assert extracted["count"] == 5

    class MockObj:
        name = "alice"
        active = False
        other = 123

    extracted_obj = extract_dto_fields(MockObj(), SampleModel)
    assert extracted_obj["name"] == "alice"
    assert extracted_obj["active"] is False
