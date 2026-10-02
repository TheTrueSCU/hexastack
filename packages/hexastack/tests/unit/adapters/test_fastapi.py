from fastapi.testclient import TestClient

from hexastack.adapters.fastapi import create_demo_app


def test_fastapi_diagnostics_integration():
    app = create_demo_app()
    assert app is not None

    client = TestClient(app)

    # 1. Health checks
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "ok"

    # 2. System info endpoint
    res_info = client.get("/_hexastack/info")
    assert res_info.status_code == 200
    data = res_info.json()
    assert "python_version" in data
    assert "installed_packages" in data

    # 3. Ping demo POST endpoint
    res_ping = client.post("/_hexastack/ping", json={"message": "from-fastapi"})
    assert res_ping.status_code == 200
    ping_data = res_ping.json()
    assert ping_data["reply"] == "PONG: from-fastapi"
    assert "correlation_id" in ping_data
