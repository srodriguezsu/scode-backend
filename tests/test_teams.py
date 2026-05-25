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

    # 2. Create Team in Tenant A attached to Project
    team_resp = await auth_client.post("/teams/", json={"project_id": proj_id})
    assert team_resp.status_code == 200
    team_id = team_resp.json()["id"]

    # 3. Add Employee to Team
    add_mem_resp = await auth_client.post(f"/teams/{team_id}/members", json=[{"employee_id": emp_id}])
    assert add_mem_resp.status_code == 200

    # 4. Verify Team Members
    read_team = await auth_client.get(f"/teams/{team_id}")
    assert len(read_team.json()["members"]) == 1

    # 5. Verify Project Teams List
    proj_teams = await auth_client.get(f"/projects/{proj_id}/teams")
    assert proj_teams.status_code == 200
    assert len(proj_teams.json()) == 1
    assert len(proj_teams.json()[0]["members"]) == 1

    # 6. Isolation Checks
    # Tenant B tries to read the team
    team_read_b = await auth_client_2.get(f"/teams/{team_id}")
    assert team_read_b.status_code == 404
    
    # Tenant B tries to add member to Tenant A's team
    team_add_b = await auth_client_2.post(f"/teams/{team_id}/members", json=[{"employee_id": emp_id}])
    assert team_add_b.status_code == 404
