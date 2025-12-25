import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from backend.api.main import create_app
from backend.api.deps import get_session_service, get_chat_service

from fastapi import FastAPI
from backend.api.routers.sessions import router as sessions_router

@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(sessions_router)
    return app

@pytest.fixture
def client(app):
    return TestClient(app)

@pytest.fixture
def mock_session_service():
    return AsyncMock()

@pytest.fixture
def mock_chat_service():
    service = AsyncMock()
    service.db = MagicMock() # DB session mock
    return service

def test_create_session(client, mock_session_service):
    session_id = uuid4()
    now = datetime.now()
    mock_session_service.create_session.return_value = session_id
    mock_session_service.get_session.return_value = {
        "id": str(session_id),
        "course_id": None,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "metadata": {"test": "data"}
    }
    
    client.app.dependency_overrides[get_session_service] = lambda: mock_session_service
    
    response = client.post("/sessions", json={"metadata": {"test": "data"}})
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(session_id)
    assert data["metadata"]["test"] == "data"
    mock_session_service.create_session.assert_called_once()

def test_list_sessions(client, mock_session_service):
    session_id = uuid4()
    now = datetime.now()
    mock_session_service.get_all_sessions.return_value = [
        {
            "id": str(session_id),
            "course_id": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "metadata": {}
        }
    ]
    
    client.app.dependency_overrides[get_session_service] = lambda: mock_session_service
    
    response = client.get("/sessions")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(session_id)

def test_delete_session(client, mock_session_service):
    session_id = uuid4()
    mock_session_service.delete_session.return_value = None
    
    client.app.dependency_overrides[get_session_service] = lambda: mock_session_service
    
    response = client.delete(f"/sessions/{session_id}")
    
    assert response.status_code == 204
    mock_session_service.delete_session.assert_called_once_with(session_id)

def test_delete_session_not_found(client, mock_session_service):
    session_id = uuid4()
    mock_session_service.delete_session.side_effect = ValueError("Session not found")
    
    client.app.dependency_overrides[get_session_service] = lambda: mock_session_service
    
    response = client.delete(f"/sessions/{session_id}")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_get_chat_history(client, mock_chat_service):
    session_id = uuid4()
    
    # We need to mock ChatHistoryAdapter which is imported inside the function
    with patch("backend.application.adapters.chat_history_adapter.ChatHistoryAdapter") as MockAdapter:
        mock_adapter_instance = MockAdapter.return_value
        mock_adapter_instance.get_messages_as_dicts = AsyncMock(return_value=[
            {"role": "human", "content": "Hello"},
            {"role": "ai", "content": "Hi there!"}
        ])
        
        client.app.dependency_overrides[get_chat_service] = lambda: mock_chat_service
        
        response = client.get(f"/sessions/{session_id}/chat/history")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["messages"][0]["role"] == "user"
        assert data["messages"][0]["content"] == "Hello"
        assert data["messages"][1]["role"] == "assistant"
        assert data["messages"][1]["content"] == "Hi there!"
