"""Unit tests for devtools inspect commands."""

from hexastack.adapters.cli.devtools.commands.inspect import (
    DemoGroupDocs,
    InspectGroupDocs,
)


def test_inspect_command_registration():
    demo = DemoGroupDocs()
    inspect_docs = InspectGroupDocs()
    assert demo is not None
    assert inspect_docs is not None
