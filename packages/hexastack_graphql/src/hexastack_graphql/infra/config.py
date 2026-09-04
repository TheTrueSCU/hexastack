from hexastack_core.infra.decorators import config_section
from hexastack_core.infra.registries.config import ConfigRegistry
from hexastack_graphql.domain.config import HexastackGraphQLConfig

config_section("graphql")(HexastackGraphQLConfig)

__all__ = [
    "HexastackGraphQLConfig",
    "register_graphql_config",
]


def register_graphql_config(registry: ConfigRegistry) -> None:
    """Register GraphQL configuration schema under 'graphql'.

    Args:
        registry: Target ConfigRegistry instance.
    """
    registry.register_config_section("graphql", HexastackGraphQLConfig)
