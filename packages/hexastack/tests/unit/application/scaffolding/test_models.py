"""Unit tests for scaffolding data models and configuration types."""

from hexastack.application.scaffolding.models import (
    ScaffoldConfig,
)


def test_scaffold_config_defaults():
    """Verify default field values of ScaffoldConfig."""
    config = ScaffoldConfig(name="order-service")
    assert config.name == "order-service"
    assert config.template == "web-api"
    assert config.description == "A modern microservice powered by Hexastack."
    assert config.python_version == ">=3.13"
    assert config.db_type == "in-memory"
    assert config.include_events is False
    assert config.include_mcp is False
    assert config.include_grpc is False
    assert config.include_graphql is False
    assert config.include_release is False
    assert config.include_openssf is False


def test_scaffold_config_custom_values():
    """Verify custom instantiation of ScaffoldConfig."""
    config = ScaffoldConfig(
        name="ai-agent",
        template="mcp-agent",
        description="Custom AI Service",
        python_version=">=3.14",
        db_type="postgres",
        include_events=True,
        include_mcp=True,
        include_grpc=True,
        include_graphql=True,
        include_release=True,
        include_openssf=True,
    )
    assert config.name == "ai-agent"
    assert config.template == "mcp-agent"
    assert config.description == "Custom AI Service"
    assert config.python_version == ">=3.14"
    assert config.db_type == "postgres"
    assert config.include_events is True
    assert config.include_mcp is True
    assert config.include_grpc is True
    assert config.include_graphql is True
    assert config.include_release is True
    assert config.include_openssf is True
