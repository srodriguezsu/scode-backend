import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_employee_crud_and_skills(auth_client: AsyncClient, auth_client_2: AsyncClient):
    # 1. Create Skill in Tenant A
    skill_resp = await auth_client.post(
        "/skills/",
        json={"name": "FastAPI", "type": "hard", "factor_type": "numeric"}
    )
    skill_id = skill_resp.json()["id"]

    # 2. Create Employee in Tenant A
    emp_resp = await auth_client.post(
        "/employees/",
        json={"national_id": "12345", "name": "Alice", "last_name": "Smith"}
    )
    assert emp_resp.status_code == 200
    emp_id = emp_resp.json()["id"]
    assert emp_resp.json()["tenant_id"] == "tenant_a" # From conftest.py auth_client

    # 3. Assign Skill to Employee in Tenant A
    assign_resp = await auth_client.post(
        f"/employees/{emp_id}/skills",
        json=[{"skill_id": skill_id, "factor": "Expert"}]
    )
    assert assign_resp.status_code == 200

    # 4. Read Employee and Verify Skills
    read_resp = await auth_client.get(f"/employees/{emp_id}")
    assert read_resp.status_code == 200
    data = read_resp.json()
    assert len(data["skills"]) == 1
    assert data["skills"][0]["name"] == "FastAPI"

    # 5. Isolation Check: Tenant B shouldn't see or mutate Tenant A's employee
    read_b = await auth_client_2.get(f"/employees/{emp_id}")
    assert read_b.status_code == 404

    update_b = await auth_client_2.put(f"/employees/{emp_id}", json={"name": "Hacked"})
    assert update_b.status_code == 404
