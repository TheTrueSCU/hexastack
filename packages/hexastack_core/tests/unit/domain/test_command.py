from hexastack_core.domain.command import Command
from hexastack_core.domain.generic import Generic


class CreateItemCommand(Command):
    item_id: str
    amount: int


def test_command_inheritance_and_properties():
    cmd = CreateItemCommand(item_id="item-123", amount=5)
    assert isinstance(cmd, Command)
    assert isinstance(cmd, Generic)
    assert cmd.item_id == "item-123"
    assert cmd.amount == 5
