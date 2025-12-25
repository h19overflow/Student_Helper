import pytest
from fastapi.testclient import TestClient
from backend.api.main import create_app

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "message": "Server Healthy"}

def test_health_check_db(client):
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "message": "Database connection OK"}

def test_health_check_vector_store(client):
    response = client.get("/api/v1/health/vector-store")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "message": "Vector store accessible"}
