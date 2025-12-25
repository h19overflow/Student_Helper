import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from backend.api.main import create_app
from backend.api.deps.dependencies import get_course_service, get_session_service

from datetime import datetime

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

@pytest.fixture
def mock_course_service():
    return AsyncMock()

@pytest.fixture
def mock_session_service():
    return AsyncMock()

def test_create_course(client, mock_course_service):
    course_id = uuid4()
    now = datetime.now()
    mock_course_service.create_course.return_value = course_id
    mock_course_service.get_course.return_value = {
        "id": str(course_id),
        "name": "Test Course",
        "description": "Test Description",
        "metadata": {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }

    client.app.dependency_overrides[get_course_service] = lambda: mock_course_service
    
    response = client.post(
        "/api/v1/courses",
        json={"name": "Test Course", "description": "Test Description"}
    )
    
    if response.status_code != 201:
        print(f"DEBUG: Response body: {response.json()}")
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Course"
    assert data["id"] == str(course_id)
    mock_course_service.create_course.assert_called_once()

def test_list_courses(client, mock_course_service):
    now = datetime.now()
    mock_course_service.get_all_courses.return_value = [
        {
            "id": str(uuid4()), 
            "name": "Course 1", 
            "description": "Desc 1", 
            "metadata": {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        },
        {
            "id": str(uuid4()), 
            "name": "Course 2", 
            "description": "Desc 2", 
            "metadata": {},
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        },
    ]

    client.app.dependency_overrides[get_course_service] = lambda: mock_course_service
    
    response = client.get("/api/v1/courses")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Course 1"
    mock_course_service.get_all_courses.assert_called_once()

def test_get_course(client, mock_course_service):
    course_id = uuid4()
    now = datetime.now()
    mock_course_service.get_course.return_value = {
        "id": str(course_id),
        "name": "Single Course",
        "description": "One Desc",
        "metadata": {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }

    client.app.dependency_overrides[get_course_service] = lambda: mock_course_service
    
    response = client.get(f"/api/v1/courses/{course_id}")
    
    assert response.status_code == 200
    assert response.json()["name"] == "Single Course"

def test_update_course(client, mock_course_service):
    course_id = uuid4()
    now = datetime.now()
    mock_course_service.update_course.return_value = {
        "id": str(course_id),
        "name": "Updated Name",
        "description": "Updated Desc",
        "metadata": {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }

    client.app.dependency_overrides[get_course_service] = lambda: mock_course_service
    
    response = client.put(
        f"/api/v1/courses/{course_id}",
        json={"name": "Updated Name"}
    )
    
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"

def test_delete_course(client, mock_course_service):
    course_id = uuid4()
    mock_course_service.delete_course.return_value = None

    client.app.dependency_overrides[get_course_service] = lambda: mock_course_service
    
    response = client.delete(f"/api/v1/courses/{course_id}")
    
    assert response.status_code == 204
    mock_course_service.delete_course.assert_called_once_with(course_id)

def test_create_course_session(client, mock_session_service):
    course_id = uuid4()
    session_id = uuid4()
    now = datetime.now()
    mock_session_service.create_session.return_value = session_id
    mock_session_service.get_session.return_value = {
        "id": str(session_id),
        "course_id": str(course_id),
        "metadata": {},
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }

    client.app.dependency_overrides[get_session_service] = lambda: mock_session_service
    
    response = client.post(
        f"/api/v1/courses/{course_id}/sessions",
        json={"metadata": {"test": "val"}}
    )
    
    assert response.status_code == 201
    assert response.json()["id"] == str(session_id)
    mock_session_service.create_session.assert_called_once()
