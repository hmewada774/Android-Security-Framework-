def test_health_endpoint(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["database"] == "healthy"
    assert "version" in data
    assert "timestamp" in data
    assert data["details"]["tables_found"] >= 4

def test_root_serves_dashboard(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Android Security Framework" in response.text
