import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_auto_tenant(unauth_client: AsyncClient):
    resp = await unauth_client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "password"}
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "tenant_id" in data
    assert data["tenant_id"] is not None

@pytest.mark.asyncio
async def test_register_specific_tenant(unauth_client: AsyncClient):
    resp = await unauth_client.post(
        "/auth/register",
        json={"email": "tenant@example.com", "password": "password", "tenant_id": "custom-tenant"}
    )
    assert resp.status_code == 201
    assert resp.json()["tenant_id"] == "custom-tenant"
