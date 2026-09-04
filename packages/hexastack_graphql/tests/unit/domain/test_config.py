from hexastack_graphql.domain.config import HexastackGraphQLConfig


def test_hexastack_graphql_config_defaults():
    cfg = HexastackGraphQLConfig()
    assert cfg.path == "/graphql"
    assert cfg.graphiql is True
    assert cfg.allow_queries is True
    assert cfg.allow_mutations is True
    assert cfg.auto_mount_fastapi is True
