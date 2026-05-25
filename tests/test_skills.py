import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_skills_crud_and_isolation(auth_client: AsyncClient, auth_client_2: AsyncClient):
    # Create in Tenant A
    resp = await auth_client.post(
        "/skills/",
        json={"name": "Python", "type": "hard", "factor_type": "numeric"}
    )
    assert resp.status_code == 200
    skill_id = resp.json()["id"]

    # Read in Tenant A
    resp_read = await auth_client.get(f"/skills/{skill_id}")
    assert resp_read.status_code == 200
    assert resp_read.json()["name"] == "Python"

    # Try to Read in Tenant B (Isolation Check)
    resp_read_b = await auth_client_2.get(f"/skills/{skill_id}")
    assert resp_read_b.status_code == 404

    # List in Tenant A vs Tenant B
    resp_list_a = await auth_client.get("/skills/")
    assert len(resp_list_a.json()) >= 1
    
    resp_list_b = await auth_client_2.get("/skills/")
    assert len(resp_list_b.json()) == 0

    # Delete in Tenant A
    resp_del = await auth_client.delete(f"/skills/{skill_id}")
    assert resp_del.status_code == 200
