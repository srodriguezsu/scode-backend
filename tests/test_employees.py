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


@pytest.mark.asyncio
async def test_employee_filtering_by_hard_skills(auth_client: AsyncClient):
    # 1. Create Skills
    resp_fastapi = await auth_client.post(
        "/skills/",
        json={"name": "FastAPI", "type": "hard", "factor_type": "numeric"}
    )
    fastapi_id = resp_fastapi.json()["id"]

    resp_react = await auth_client.post(
        "/skills/",
        json={"name": "React", "type": "hard", "factor_type": "numeric"}
    )
    react_id = resp_react.json()["id"]

    resp_comm = await auth_client.post(
        "/skills/",
        json={"name": "Communication", "type": "soft", "factor_type": "categorical"}
    )
    comm_id = resp_comm.json()["id"]

    # 2. Create Employees
    # Alice: FastAPI (hard), React (hard)
    resp_alice = await auth_client.post(
        "/employees/",
        json={"national_id": "10001", "name": "Alice", "last_name": "One"}
    )
    alice_id = resp_alice.json()["id"]
    await auth_client.post(
        f"/employees/{alice_id}/skills",
        json=[
            {"skill_id": fastapi_id, "factor": "5"},
            {"skill_id": react_id, "factor": "4"}
        ]
    )

    # Bob: React (hard), Communication (soft)
    resp_bob = await auth_client.post(
        "/employees/",
        json={"national_id": "10002", "name": "Bob", "last_name": "Two"}
    )
    bob_id = resp_bob.json()["id"]
    await auth_client.post(
        f"/employees/{bob_id}/skills",
        json=[
            {"skill_id": react_id, "factor": "3"},
            {"skill_id": comm_id, "factor": "High"}
        ]
    )

    # Charlie: Communication (soft) only
    resp_charlie = await auth_client.post(
        "/employees/",
        json={"national_id": "10003", "name": "Charlie", "last_name": "Three"}
    )
    charlie_id = resp_charlie.json()["id"]
    await auth_client.post(
        f"/employees/{charlie_id}/skills",
        json=[
            {"skill_id": comm_id, "factor": "Medium"}
        ]
    )

    # 3. Test filtering: filter by FastAPI
    resp = await auth_client.get(f"/employees/?skill_ids={fastapi_id}")
    assert resp.status_code == 200
    employees = resp.json()
    assert len(employees) == 1
    assert employees[0]["id"] == alice_id

    # 4. Test filtering: filter by React
    resp = await auth_client.get(f"/employees/?skill_ids={react_id}")
    assert resp.status_code == 200
    employees = resp.json()
    assert len(employees) == 2
    employee_ids = {e["id"] for e in employees}
    assert employee_ids == {alice_id, bob_id}

    # 5. Test filtering: filter by FastAPI and React (match_all=True, default)
    # Comma-separated
    resp = await auth_client.get(f"/employees/?skill_ids={fastapi_id},{react_id}")
    assert resp.status_code == 200
    employees = resp.json()
    assert len(employees) == 1
    assert employees[0]["id"] == alice_id

    # Multiple query params
    resp = await auth_client.get(f"/employees/?skill_ids={fastapi_id}&skill_ids={react_id}")
    assert resp.status_code == 200
    employees = resp.json()
    assert len(employees) == 1
    assert employees[0]["id"] == alice_id

    # 6. Test filtering: filter by FastAPI and React (match_all=False)
    resp = await auth_client.get(f"/employees/?skill_ids={fastapi_id},{react_id}&match_all=false")
    assert resp.status_code == 200
    employees = resp.json()
    assert len(employees) == 2
    employee_ids = {e["id"] for e in employees}
    assert employee_ids == {alice_id, bob_id}

    # 7. Test filtering by soft skill (should be ignored / return no matches under hard skill filter)
    resp = await auth_client.get(f"/employees/?skill_ids={comm_id}")
    assert resp.status_code == 200
    employees = resp.json()
    assert len(employees) == 0

    # 8. Test filtering: combination of hard skill and soft skill with match_all=True (default)
    # Since one of the requested skill IDs is a soft skill, match_all=True should yield 0 results.
    resp = await auth_client.get(f"/employees/?skill_ids={fastapi_id},{comm_id}")
    assert resp.status_code == 200
    employees = resp.json()
    assert len(employees) == 0

    # 9. Test filtering: combination of hard skill and soft skill with match_all=False
    # Since match_all=False, the soft skill is ignored but the hard skill FastAPI matches Alice.
    resp = await auth_client.get(f"/employees/?skill_ids={fastapi_id},{comm_id}&match_all=false")
    assert resp.status_code == 200
    employees = resp.json()
    assert len(employees) == 1
    assert employees[0]["id"] == alice_id

