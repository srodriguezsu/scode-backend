import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_team_crud_and_members(auth_client: AsyncClient, auth_client_2: AsyncClient):
    # 1. Setup Data in Tenant A
    # Create Project
    proj_resp = await auth_client.post("/projects/", json={"name": "Test Project"})
    proj_id = proj_resp.json()["id"]

    # Create Employee
    emp_resp = await auth_client.post("/employees/", json={"national_id": "999", "name": "Bob"})
    emp_id = emp_resp.json()["id"]

    # 2. Create Team in Tenant A attached to Project (defaulting predicted_cohesion_index to None)
    team_resp = await auth_client.post("/teams/", json={"project_id": proj_id})
    assert team_resp.status_code == 200, team_resp.json()
    team_data = team_resp.json()
    assert team_data["predicted_cohesion_index"] is None
    team_id = team_data["id"]

    # Create another Team with a specified predicted_cohesion_index
    team_2_resp = await auth_client.post(
        "/teams/", 
        json={"project_id": proj_id, "predicted_cohesion_index": 0.85}
    )
    assert team_2_resp.status_code == 200
    team_2_data = team_2_resp.json()
    assert team_2_data["predicted_cohesion_index"] == 0.85
    team_2_id = team_2_data["id"]

    # 3. Add Employee to Team
    add_mem_resp = await auth_client.post(f"/teams/{team_id}/members", json=[{"employee_id": emp_id}])
    assert add_mem_resp.status_code == 200

    # 4. Verify Team Members & predicted_cohesion_index on read
    read_team = await auth_client.get(f"/teams/{team_id}")
    assert len(read_team.json()["members"]) == 1
    assert read_team.json()["predicted_cohesion_index"] is None

    read_team_2 = await auth_client.get(f"/teams/{team_2_id}")
    assert read_team_2.json()["predicted_cohesion_index"] == 0.85

    # 5. Verify Project Teams List
    proj_teams = await auth_client.get(f"/projects/{proj_id}/teams")
    assert proj_teams.status_code == 200
    assert len(proj_teams.json()) == 2
    # Ensure team_2 has the predicted_cohesion_index in the project teams list
    teams_by_id = {t["id"]: t for t in proj_teams.json()}
    assert teams_by_id[team_id]["predicted_cohesion_index"] is None
    assert teams_by_id[team_2_id]["predicted_cohesion_index"] == 0.85
    assert len(teams_by_id[team_id]["members"]) == 1

    # 6. Isolation Checks
    # Tenant B tries to read the team
    team_read_b = await auth_client_2.get(f"/teams/{team_id}")
    assert team_read_b.status_code == 404
    
    # Tenant B tries to add member to Tenant A's team
    team_add_b = await auth_client_2.post(f"/teams/{team_id}/members", json=[{"employee_id": emp_id}])
    assert team_add_b.status_code == 404


@pytest.mark.asyncio
async def test_create_team_with_employee_ids(auth_client: AsyncClient, auth_client_2: AsyncClient):
    # 1. Setup Data in Tenant A
    proj_resp = await auth_client.post("/projects/", json={"name": "Tenant A Project"})
    proj_id = proj_resp.json()["id"]

    emp_resp_1 = await auth_client.post("/employees/", json={"national_id": "111", "name": "Bob"})
    emp_id_1 = emp_resp_1.json()["id"]
    emp_resp_2 = await auth_client.post("/employees/", json={"national_id": "222", "name": "Alice"})
    emp_id_2 = emp_resp_2.json()["id"]

    # 2. Setup Data in Tenant B
    emp_resp_b = await auth_client_2.post("/employees/", json={"national_id": "333", "name": "Charlie"})
    emp_id_b = emp_resp_b.json()["id"]

    # 3. Create Team directly with Tenant A employees
    create_resp = await auth_client.post(
        "/teams/",
        json={
            "project_id": proj_id,
            "employee_ids": [emp_id_1, emp_id_2],
            "predicted_cohesion_index": 0.92
        }
    )
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["predicted_cohesion_index"] == 0.92
    assert len(create_data["members"]) == 2
    member_ids = {m["id"] for m in create_data["members"]}
    assert member_ids == {emp_id_1, emp_id_2}
    team_id = create_data["id"]

    # 4. Try to Create Team with an Employee from Tenant B (should fail)
    fail_resp = await auth_client.post(
        "/teams/",
        json={
            "project_id": proj_id,
            "employee_ids": [emp_id_1, emp_id_b]
        }
    )
    assert fail_resp.status_code == 404

    # 5. Verify Team & members via Read
    read_resp = await auth_client.get(f"/teams/{team_id}")
    assert read_resp.status_code == 200
    read_data = read_resp.json()
    assert len(read_data["members"]) == 2
    assert {m["id"] for m in read_data["members"]} == {emp_id_1, emp_id_2}

    # 6. Verify via Project Teams List
    proj_teams = await auth_client.get(f"/projects/{proj_id}/teams")
    assert proj_teams.status_code == 200
    assert len(proj_teams.json()) == 1
    assert len(proj_teams.json()[0]["members"]) == 2

