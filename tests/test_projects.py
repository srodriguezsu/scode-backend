import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_project_crud_and_skills(auth_client: AsyncClient, auth_client_2: AsyncClient):
    # Create a Hard Skill in Tenant A
    skill_resp = await auth_client.post(
        "/skills/",
        json={"name": "Docker", "type": "hard", "factor_type": "numeric"}
    )
    hard_skill_id = skill_resp.json()["id"]

    # Create a Soft Skill in Tenant A
    soft_skill_resp = await auth_client.post(
        "/skills/",
        json={"name": "Communication", "type": "soft", "factor_type": "categorical"}
    )
    soft_skill_id = soft_skill_resp.json()["id"]

    # Create Project in Tenant A
    proj_resp = await auth_client.post(
        "/projects/",
        json={"name": "Cloud Migration", "description": "Migrate", "max_teams": 3}
    )
    assert proj_resp.status_code == 200
    proj_id = proj_resp.json()["id"]
    assert proj_resp.json()["tenant_id"] == "tenant_a"

    # Attach Hard Skill
    attach_hard = await auth_client.post(
        f"/projects/{proj_id}/skills",
        json=[{"skill_id": hard_skill_id}]
    )
    assert attach_hard.status_code == 200

    # Attach Soft Skill (Should fail business logic)
    attach_soft = await auth_client.post(
        f"/projects/{proj_id}/skills",
        json=[{"skill_id": soft_skill_id}]
    )
    assert attach_soft.status_code == 400

    # Isolation Check: Tenant B shouldn't see or mutate project
    read_b = await auth_client_2.get(f"/projects/{proj_id}")
    assert read_b.status_code == 404
