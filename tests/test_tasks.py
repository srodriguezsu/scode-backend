import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_task_crud_metrics_and_isolation(auth_client: AsyncClient, auth_client_2: AsyncClient):
    # --- SETUP: Create project and employee in Tenant A ---
    proj_resp = await auth_client.post(
        "/projects/",
        json={"name": "Antigravity Project", "description": "Awesome workspace"}
    )
    assert proj_resp.status_code == 200
    proj_data = proj_resp.json()
    proj_id = proj_data["id"]
    assert proj_data["total_tasks"] == 0
    assert proj_data["completed_tasks"] == 0

    emp_resp = await auth_client.post(
        "/employees/",
        json={"national_id": "12345", "name": "Alice", "last_name": "Smith"}
    )
    assert emp_resp.status_code == 200
    emp_id = emp_resp.json()["id"]

    # --- SETUP: Create project and employee in Tenant B ---
    proj_b_resp = await auth_client_2.post(
        "/projects/",
        json={"name": "Other Project", "description": "Other description"}
    )
    assert proj_b_resp.status_code == 200
    proj_b_id = proj_b_resp.json()["id"]

    emp_b_resp = await auth_client_2.post(
        "/employees/",
        json={"national_id": "67890", "name": "Bob", "last_name": "Jones"}
    )
    assert emp_b_resp.status_code == 200
    emp_b_id = emp_b_resp.json()["id"]

    # --- ISOLATION TEST: Tenant B trying to create a task in Tenant A's project ---
    task_fail = await auth_client_2.post(
        "/tasks/",
        json={
            "title": "Malicious Task",
            "project_id": proj_id,
            "employee_id": emp_b_id
        }
    )
    assert task_fail.status_code == 404

    # --- ISOLATION TEST: Tenant A trying to assign to Tenant B's employee ---
    task_fail_emp = await auth_client.post(
        "/tasks/",
        json={
            "title": "Cross Tenant Employee Task",
            "project_id": proj_id,
            "employee_id": emp_b_id
        }
    )
    assert task_fail_emp.status_code == 404

    # --- CRUD: Create first task (uncompleted) in Tenant A ---
    task1_resp = await auth_client.post(
        "/tasks/",
        json={
            "title": "Setup repository",
            "description": "Initialize poetry and git",
            "completed": False,
            "project_id": proj_id,
            "employee_id": emp_id
        }
    )
    assert task1_resp.status_code == 200
    task1_data = task1_resp.json()
    task1_id = task1_data["id"]
    assert task1_data["tenant_id"] == "tenant_a"
    assert task1_data["completed"] is False

    # Check project total_tasks and completed_tasks are updated
    proj_after_1 = await auth_client.get(f"/projects/{proj_id}")
    assert proj_after_1.json()["total_tasks"] == 1
    assert proj_after_1.json()["completed_tasks"] == 0

    # --- CRUD: Create second task (completed) in Tenant A ---
    task2_resp = await auth_client.post(
        "/tasks/",
        json={
            "title": "Write readme",
            "description": "Basic info",
            "completed": True,
            "project_id": proj_id,
            "employee_id": emp_id
        }
    )
    assert task2_resp.status_code == 200
    task2_id = task2_resp.json()["id"]

    # Check project total_tasks and completed_tasks are updated
    proj_after_2 = await auth_client.get(f"/projects/{proj_id}")
    assert proj_after_2.json()["total_tasks"] == 2
    assert proj_after_2.json()["completed_tasks"] == 1

    # --- CRUD: Read tasks list ---
    tasks_list_resp = await auth_client.get("/tasks/")
    assert tasks_list_resp.status_code == 200
    tasks = tasks_list_resp.json()
    assert len(tasks) == 2

    # Filtering checks
    tasks_completed_resp = await auth_client.get("/tasks/?completed=true")
    assert len(tasks_completed_resp.json()) == 1
    assert tasks_completed_resp.json()[0]["id"] == task2_id

    # --- ISOLATION TEST: Tenant B cannot list Tenant A's tasks ---
    tasks_list_b_resp = await auth_client_2.get("/tasks/")
    assert len(tasks_list_b_resp.json()) == 0

    # --- ISOLATION TEST: Tenant B cannot read Tenant A's task detail ---
    task_detail_b = await auth_client_2.get(f"/tasks/{task1_id}")
    assert task_detail_b.status_code == 404

    # --- CRUD: Update task to completed ---
    update_resp = await auth_client.patch(
        f"/tasks/{task1_id}",
        json={"completed": True, "description": "Updated description"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["completed"] is True
    assert update_resp.json()["description"] == "Updated description"

    # Check project metrics updated
    proj_after_update = await auth_client.get(f"/projects/{proj_id}")
    assert proj_after_update.json()["total_tasks"] == 2
    assert proj_after_update.json()["completed_tasks"] == 2

    # --- ISOLATION TEST: Tenant B cannot update Tenant A's task ---
    update_fail = await auth_client_2.patch(
        f"/tasks/{task1_id}",
        json={"completed": False}
    )
    assert update_fail.status_code == 404

    # --- CRUD: Delete task ---
    del_resp = await auth_client.delete(f"/tasks/{task2_id}")
    assert del_resp.status_code == 200

    # Check project metrics updated (task2 is deleted, so total_tasks = 1, completed = 1)
    proj_after_delete = await auth_client.get(f"/projects/{proj_id}")
    assert proj_after_delete.json()["total_tasks"] == 1
    assert proj_after_delete.json()["completed_tasks"] == 1

    # --- ISOLATION TEST: Tenant B cannot delete Tenant A's task ---
    del_fail = await auth_client_2.delete(f"/tasks/{task1_id}")
    assert del_fail.status_code == 404
