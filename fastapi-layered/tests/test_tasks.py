import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_login(
    client: AsyncClient, email: str, full_name: str = "Task Owner"
) -> str:
    password = "SuperSecreta123"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": full_name, "password": password},
    )
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    return response.json()["access_token"]


async def test_tasks_crud(client: AsyncClient):
    token = await _register_and_login(client, "task-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = await client.post(
        "/api/v1/tasks",
        json={"title": "Aprender FastAPI", "description": "Implementar una entidad"},
        headers=headers,
    )
    assert create_response.status_code == 201
    task = create_response.json()
    assert task["title"] == "Aprender FastAPI"
    assert task["completed"] is False
    assert task["owner_id"]

    list_response = await client.get("/api/v1/tasks", headers=headers)
    assert list_response.status_code == 200
    assert list_response.json()["total"] == 1

    update_response = await client.put(
        f"/api/v1/tasks/{task['id']}",
        json={"completed": True},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["completed"] is True

    delete_response = await client.delete(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/tasks/{task['id']}", headers=headers)
    assert get_response.status_code == 404


async def test_tasks_require_authentication(client: AsyncClient):
    response = await client.get("/api/v1/tasks")
    assert response.status_code == 401


async def test_user_cannot_access_another_users_task(client: AsyncClient):
    owner_token = await _register_and_login(client, "task-owner-2@example.com")
    owner_headers = {"Authorization": f"Bearer {owner_token}"}
    create_response = await client.post(
        "/api/v1/tasks",
        json={"title": "Privada"},
        headers=owner_headers,
    )
    task_id = create_response.json()["id"]

    other_token = await _register_and_login(client, "task-other@example.com", "Other User")
    other_headers = {"Authorization": f"Bearer {other_token}"}
    response = await client.get(f"/api/v1/tasks/{task_id}", headers=other_headers)

    assert response.status_code == 404
