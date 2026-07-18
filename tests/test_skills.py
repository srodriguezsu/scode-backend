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


@pytest.mark.asyncio
async def test_skills_filtering_by_type(auth_client: AsyncClient):
    # 1. Create one hard skill and one soft skill
    resp_hard = await auth_client.post(
        "/skills/",
        json={"name": "Go", "type": "hard", "factor_type": "numeric"}
    )
    assert resp_hard.status_code == 200
    hard_id = resp_hard.json()["id"]

    resp_soft = await auth_client.post(
        "/skills/",
        json={"name": "Teamwork", "type": "soft", "factor_type": "categorical"}
    )
    assert resp_soft.status_code == 200
    soft_id = resp_soft.json()["id"]

    # 2. Filter by hard skills
    resp = await auth_client.get("/skills/?type=hard")
    assert resp.status_code == 200
    skills = resp.json()
    # Check that Go is present, but Teamwork is not
    skill_ids = [s["id"] for s in skills]
    assert hard_id in skill_ids
    assert soft_id not in skill_ids

    # 3. Filter by soft skills
    resp = await auth_client.get("/skills/?type=soft")
    assert resp.status_code == 200
    skills = resp.json()
    # Check that Teamwork is present, but Go is not
    skill_ids = [s["id"] for s in skills]
    assert soft_id in skill_ids
    assert hard_id not in skill_ids

    # 4. Check invalid type (should fail with validation error / 422)
    resp = await auth_client.get("/skills/?type=invalid")
    assert resp.status_code == 422

    # Clean up
    await auth_client.delete(f"/skills/{hard_id}")
    await auth_client.delete(f"/skills/{soft_id}")

