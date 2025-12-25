import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from uuid import uuid4
from datetime import datetime

from backend.api.main import create_app
from backend.api.deps import get_job_service

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def mock_job_service():
    return AsyncMock()

def test_get_job_status(client, mock_job_service):
    job_id = uuid4()
    now = datetime.now()
    mock_job_service.get_job_status.return_value = {
        "id": str(job_id),
        "task_id": "task-123",
        "type": "document_ingestion",
        "status": "completed",
        "progress": 100,
        "result": {"doc_id": "doc-456"},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    client.app.dependency_overrides[get_job_service] = lambda: mock_job_service
    
    response = client.get(f"/api/v1/jobs/{job_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["progress"] == 100
    mock_job_service.get_job_status.assert_called_once_with(job_id)

def test_get_job_not_found(client, mock_job_service):
    job_id = uuid4()
    mock_job_service.get_job_status.side_effect = ValueError(f"Job {job_id} not found")
    
    client.app.dependency_overrides[get_job_service] = lambda: mock_job_service
    
    response = client.get(f"/api/v1/jobs/{job_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
