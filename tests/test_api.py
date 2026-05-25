import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_and_read_skill(client: AsyncClient):
    # Test Create
    response = await client.post(
        "/skills/",
        json={"name": "Python", "type": "hard", "factor_type": "numeric"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Python"
    assert data["type"] == "hard"
    assert "id" in data
    skill_id = data["id"]

    # Test Read Single
    response = await client.get(f"/skills/{skill_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Python"

    # Test Read All
    response = await client.get("/skills/")
    assert response.status_code == 200
    assert len(response.json()) > 0


@pytest.mark.asyncio
async def test_create_employee_and_assign_skill(client: AsyncClient):
    # Create Skill first
    skill_resp = await client.post(
        "/skills/",
        json={"name": "FastAPI", "type": "hard", "factor_type": "categorical"}
    )
    skill_id = skill_resp.json()["id"]

    # Create Employee
    emp_resp = await client.post(
        "/employees/",
        json={"national_id": "1234567890", "name": "John", "last_name": "Doe"}
    )
    assert emp_resp.status_code == 200
    emp_id = emp_resp.json()["id"]

    # Assign Skill to Employee
    assign_resp = await client.post(
        f"/employees/{emp_id}/skills",
        json=[{"skill_id": skill_id, "factor": "Expert"}]
    )
    assert assign_resp.status_code == 200
    assert assign_resp.json()["ok"] is True

    # Read Employee with Skills
    read_emp_resp = await client.get(f"/employees/{emp_id}")
    assert read_emp_resp.status_code == 200
    data = read_emp_resp.json()
    assert len(data["skills"]) == 1
    assert data["skills"][0]["name"] == "FastAPI"
    assert data["skills"][0]["factor"] == "Expert"


@pytest.mark.asyncio
async def test_create_project_and_attach_skills(client: AsyncClient):
    # Create a Hard Skill
    skill_resp = await client.post(
        "/skills/",
        json={"name": "Docker", "type": "hard", "factor_type": "numeric"}
    )
    skill_id = skill_resp.json()["id"]

    # Create a Soft Skill (to test failure)
    soft_skill_resp = await client.post(
        "/skills/",
        json={"name": "Communication", "type": "soft", "factor_type": "categorical"}
    )
    soft_skill_id = soft_skill_resp.json()["id"]

    # Create Project
    proj_resp = await client.post(
        "/projects/",
        json={"name": "Migration Project", "description": "Migrate to Docker", "max_teams": 2}
    )
    assert proj_resp.status_code == 200
    proj_id = proj_resp.json()["id"]

    # Attach Hard Skill (Should Succeed)
    attach_resp = await client.post(
        f"/projects/{proj_id}/skills",
        json=[{"skill_id": skill_id}]
    )
    assert attach_resp.status_code == 200

    # Attach Soft Skill (Should Fail based on requirements)
    attach_fail_resp = await client.post(
        f"/projects/{proj_id}/skills",
        json=[{"skill_id": soft_skill_id}]
    )
    assert attach_fail_resp.status_code == 400
    assert "not a hard skill" in attach_fail_resp.json()["detail"]
