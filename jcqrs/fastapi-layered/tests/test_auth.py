"""Tests de la capa API para registro y login (auth)."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_register_creates_user(client: AsyncClient, user_payload: dict):
    response = await client.post("/api/v1/auth/register", json=user_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == user_payload["email"]
    assert "password" not in body
    assert "hashed_password" not in body


async def test_register_duplicate_email_returns_409(client: AsyncClient, user_payload: dict):
    await client.post("/api/v1/auth/register", json=user_payload)
    response = await client.post("/api/v1/auth/register", json=user_payload)

    assert response.status_code == 409


async def test_login_with_valid_credentials_returns_token(client: AsyncClient, user_payload: dict):
    await client.post("/api/v1/auth/register", json=user_payload)

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": user_payload["email"], "password": user_payload["password"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


async def test_login_with_wrong_password_returns_401(client: AsyncClient, user_payload: dict):
    await client.post("/api/v1/auth/register", json=user_payload)

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": user_payload["email"], "password": "incorrecta"},
    )

    assert response.status_code == 401
