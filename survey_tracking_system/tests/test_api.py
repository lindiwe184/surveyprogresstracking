import json

from backend.app import create_app


def test_health_endpoint():
    app = create_app()
    client = app.test_client()
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = json.loads(resp.data.decode())
    assert data.get("status") == "ok"


