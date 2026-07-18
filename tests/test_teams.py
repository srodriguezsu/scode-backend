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
    assert team_resp.status_code == 200
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
