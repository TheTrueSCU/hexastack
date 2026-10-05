from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_graphql.infra.config import (
    HexastackGraphQLConfig,
    register_graphql_config,
)


def test_graphql_config_defaults():
    cfg = HexastackGraphQLConfig()
    assert cfg.path == "/graphql"
    assert cfg.graphiql is True
    assert cfg.allow_queries is True
    assert cfg.allow_mutations is True
    assert cfg.auto_mount_fastapi is True
    assert cfg.title == "Hexastack GraphQL API"


def test_register_graphql_config():
    reg = ConfigRegistry()
    register_graphql_config(reg)
    assert "graphql" in reg.all
    assert reg.all["graphql"] is HexastackGraphQLConfig
