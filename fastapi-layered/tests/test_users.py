"""Tests de la capa API para el recurso protegido /users."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register_and_login(client: AsyncClient, user_payload: dict) -> str:
    await client.post("/api/v1/auth/register", json=user_payload)
    login_response = await client.post(
        "/api/v1/auth/login",
        data={"username": user_payload["email"], "password": user_payload["password"]},
    )
    return login_response.json()["access_token"]


async def test_get_me_requires_authentication(client: AsyncClient):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_get_me_returns_current_user(client: AsyncClient, user_payload: dict):
    token = await _register_and_login(client, user_payload)

    response = await client.get(
        "/api/v1/users/me", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    assert response.json()["email"] == user_payload["email"]


async def test_user_cannot_access_another_users_resource(client: AsyncClient, user_payload: dict):
    token = await _register_and_login(client, user_payload)

    other_user = {
        "email": "grace.hopper@example.com",
        "full_name": "Grace Hopper",
        "password": "OtraSuperSecreta123",
    }
    await client.post("/api/v1/auth/register", json=other_user)

    # El usuario 1 (id=1) intenta leer al usuario 2 (id=2): debe ser 403.
    response = await client.get(
        "/api/v1/users/2", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403


async def test_list_users_is_paginated(client: AsyncClient, user_payload: dict):
    token = await _register_and_login(client, user_payload)

    response = await client.get(
        "/api/v1/users?page=1&page_size=10",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert body["total"] >= 1
