import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime, timedelta

from backend.api.main import create_app
from backend.api.deps import get_visual_knowledge_service, get_s3_document_client
from backend.boundary.db import get_async_db

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def mock_vk_service():
    return AsyncMock()

@pytest.fixture
def mock_s3_client():
    return MagicMock()

@pytest.fixture
def mock_db():
    return AsyncMock()

def test_generate_visual_knowledge(client, mock_vk_service):
    session_id = str(uuid4())
    mock_vk_service.generate.return_value = {
        "s3_key": f"sessions/{session_id}/images/123.png",
        "presigned_url": "https://s3.example.com/123.png",
        "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
        "mime_type": "image/png",
        "message_index": 1,
        "main_concepts": ["Concept A"],
        "branches": [{"id": "b1", "label": "L1", "description": "D1"}],
        "image_generation_prompt": "Prompt"
    }
    
    client.app.dependency_overrides[get_visual_knowledge_service] = lambda: mock_vk_service
    
    response = client.post(
        f"/api/v1/sessions/{session_id}/visual-knowledge",
        json={"ai_answer": "Test answer", "message_index": 1}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["s3_key"] == f"sessions/{session_id}/images/123.png"
    assert data["main_concepts"] == ["Concept A"]
    mock_vk_service.generate.assert_called_once()

def test_get_session_images(client, mock_s3_client, mock_db):
    session_id = str(uuid4())
    
    # Mock image_crud.get_by_session_id
    mock_image = MagicMock()
    mock_image.s3_key = "key1"
    mock_image.mime_type = "image/png"
    mock_image.message_index = 0
    mock_image.main_concepts = ["C1"]
    mock_image.branches = [{"id": "b1", "label": "L1", "description": "D1"}]
    mock_image.image_generation_prompt = "P1"
    
    with patch("backend.api.routers.visual_knowledge.image_crud") as mock_crud:
        mock_crud.get_by_session_id = AsyncMock(return_value=[mock_image])
        
        mock_s3_client.generate_presigned_download_url.return_value = (
            "https://presigned.url", 
            datetime.now() + timedelta(hours=1)
        )
        
        client.app.dependency_overrides[get_async_db] = lambda: mock_db
        client.app.dependency_overrides[get_s3_document_client] = lambda: mock_s3_client
        
        response = client.get(f"/api/v1/sessions/{session_id}/images")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["presigned_url"] == "https://presigned.url"
        mock_crud.get_by_session_id.assert_called_once()
        mock_s3_client.generate_presigned_download_url.assert_called_once()

def test_get_session_images_invalid_id(client):
    response = client.get("/api/v1/sessions/invalid-id/images")
    assert response.status_code == 400
    assert "invalid session id" in response.json()["detail"].lower()
