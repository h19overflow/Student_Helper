import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from datetime import datetime

from backend.api.main import create_app
from backend.api.deps.dependencies import (
    get_s3_document_client,
    get_job_service,
    get_document_service,
)

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def mock_s3_client():
    client = MagicMock()
    # handle_presigned_url_request is not async
    return client

@pytest.fixture
def mock_job_service():
    service = AsyncMock()
    service.db = AsyncMock()
    return service

@pytest.fixture
def mock_document_service():
    return AsyncMock()

def test_create_presigned_upload_url(client, mock_s3_client):
    session_id = uuid4()
    now = datetime.now()
    mock_s3_client.generate_presigned_url.return_value = (
        "https://s3.amazonaws.com/test-bucket/test.pdf?signature=...",
        now
    )
    
    # handle_presigned_url_request is called in the router
    # We need to mock the dependency get_s3_document_client
    client.app.dependency_overrides[get_s3_document_client] = lambda: mock_s3_client
    
    response = client.post(
        f"/api/v1/sessions/{session_id}/docs/presigned-url",
        json={"filename": "test.pdf", "content_type": "application/pdf"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "presigned_url" in data
    assert "s3_key" in data
    assert data["presigned_url"].startswith("https://s3.amazonaws.com")

def test_document_uploaded_to_s3(client, mock_job_service):
    session_id = uuid4()
    job_id = uuid4()
    mock_job_service.create_job.return_value = job_id
    
    client.app.dependency_overrides[get_job_service] = lambda: mock_job_service
    
    response = client.post(
        f"/api/v1/sessions/{session_id}/docs/uploaded",
        json={"s3_key": "some/key", "filename": "test.pdf"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["jobId"] == str(job_id)
    assert data["status"] == "pending"
    mock_job_service.create_job.assert_called_once()
    mock_job_service.db.commit.assert_called_once()

def test_delete_document(client, mock_document_service):
    session_id = uuid4()
    doc_id = uuid4()
    mock_document_service.delete_document.return_value = None
    
    client.app.dependency_overrides[get_document_service] = lambda: mock_document_service
    
    response = client.delete(f"/api/v1/sessions/{session_id}/docs/{doc_id}")
    
    assert response.status_code == 204
    mock_document_service.delete_document.assert_called_once_with(
        doc_id=doc_id,
        session_id=session_id
    )

def test_get_documents(client, mock_document_service):
    session_id = uuid4()
    now = datetime.now()
    
    # Mock return value needs to be list of objects with attributes
    mock_doc = MagicMock()
    mock_doc.id = uuid4()
    mock_doc.session_id = session_id
    mock_doc.name = "test.pdf"
    mock_doc.status = MagicMock()
    mock_doc.status.value = "ready"
    mock_doc.created_at = now
    mock_doc.error_message = None
    
    mock_document_service.get_session_documents.return_value = [mock_doc]
    
    client.app.dependency_overrides[get_document_service] = lambda: mock_document_service
    
    response = client.get(f"/api/v1/sessions/{session_id}/docs")
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["documents"][0]["name"] == "test.pdf"
    assert data["documents"][0]["status"] == "ready"
