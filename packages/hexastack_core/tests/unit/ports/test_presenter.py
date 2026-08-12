from typing import Any

from hexastack_core.domain.generic import Generic
from hexastack_core.ports.presenter import Presenter


class SampleOutput(Generic):
    text: str


class JsonPresenter(Presenter):
    def present(self, instance: Generic) -> Any | None:
        if isinstance(instance, SampleOutput):
            return {"formatted_text": instance.text}
        return None


def test_presenter_interface():
    presenter = JsonPresenter()
    output = SampleOutput(text="hello world")
    presented = presenter.present(output)

    assert presented == {"formatted_text": "hello world"}
