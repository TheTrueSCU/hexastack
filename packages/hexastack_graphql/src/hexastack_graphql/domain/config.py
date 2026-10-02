from pydantic import BaseModel, Field


class HexastackGraphQLConfig(BaseModel):
    """Configuration schema for Hexastack Strawberry GraphQL adapter.

    Notes/Architectural Intent:
        Controls GraphQL routing, GraphiQL interactive playground, mutation enabling,
        and automatic mounting into FastAPI applications.
    """

    path: str = Field(
        default="/graphql",
        description="HTTP path prefix for GraphQL queries and mutations.",
    )
    graphiql: bool = Field(
        default=True,
        description="Enable interactive GraphiQL web interface.",
    )
    allow_queries: bool = Field(
        default=True,
        description="Enable GraphQL query execution.",
    )
    allow_mutations: bool = Field(
        default=True,
        description="Enable GraphQL mutation execution.",
    )
    auto_mount_fastapi: bool = Field(
        default=True,
        description="Automatically mount GraphQLRouter into FastAPI application during bootstrap.",
    )
    title: str = Field(
        default="Hexastack GraphQL API",
        description="GraphQL schema / API title.",
    )


__all__ = [
    "HexastackGraphQLConfig",
]
