"""Unit tests for scaffolding tests templates."""

from hexastack.application.scaffolding.templates import tests


def test_tests_template_module_exports():
    """Verify test renderers generate valid Python test snippets."""
    pkg = "test_pkg"
    assert "InMemoryItemRepository" in tests.render_test_conftest(pkg)
    assert "assert_clean_architecture" in tests.render_test_architecture(pkg)
    assert "test_item_entity_creation" in tests.render_test_domain(pkg)
    assert "test_item_creation" in tests.render_test_domain_models(pkg)
    assert "test_create_item_command" in tests.render_test_domain_commands(pkg)
    assert "ItemRepositoryPort" in tests.render_test_ports_repositories(pkg)
    assert "InMemoryItemRepository" in tests.render_test_adapters_database(pkg)
    assert "test_cli_module_loaded" in tests.render_test_adapters_cli(pkg)
    assert "http_adapter" in tests.render_test_adapters_http(pkg)
    assert "grpc_adapter" in tests.render_test_adapters_grpc(pkg)
    assert "graphql_adapter" in tests.render_test_adapters_graphql(pkg)
    assert "mcp_adapter" in tests.render_test_adapters_mcp(pkg)
    assert "AppConfig" in tests.render_test_infra_config(pkg)
    assert "handle_create_item" in tests.render_test_infra_handlers(pkg)
    assert "create_app" in tests.render_test_infra_bootstrap(pkg)
    assert "test_package_has_docstring" in tests.render_test_root_init(pkg)
    assert "test_domain_package_loaded" in tests.render_test_subpackage_init(
        pkg, "domain"
    )
    assert "given" in tests.render_test_domain_fuzz(pkg)
