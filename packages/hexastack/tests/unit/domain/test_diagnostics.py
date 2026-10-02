from hexastack.domain.diagnostics import (
    GetSystemInfoQuery,
    PingDemoCommand,
    PingDemoDTO,
    RegistryInfoDTO,
    SystemInfoDTO,
)


def test_diagnostics_models():
    info = SystemInfoDTO(
        python_version="3.13.0",
        platform="Linux",
        installed_packages={"hexastack-core": "0.1.0"},
        optional_dependencies={"rich": True},
    )
    assert info.python_version == "3.13.0"
    assert info.platform == "Linux"
    assert info.installed_packages["hexastack-core"] == "0.1.0"
    assert info.optional_dependencies["rich"] is True

    qry = GetSystemInfoQuery()
    assert qry is not None

    reg_dto = RegistryInfoDTO(
        commands=["PingDemoCommand"],
        queries=["GetSystemInfoQuery"],
        configs=["cli", "fastapi"],
    )
    assert len(reg_dto.commands) == 1
    assert len(reg_dto.queries) == 1
    assert len(reg_dto.configs) == 2

    ping = PingDemoCommand(message="hello")
    assert ping.message == "hello"

    pong = PingDemoDTO(reply="PONG: hello", correlation_id="cid-123")
    assert pong.reply == "PONG: hello"
    assert pong.correlation_id == "cid-123"
