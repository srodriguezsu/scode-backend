from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, col
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.auth import current_active_user
from app.models import (
    Task,
    TaskCreate,
    TaskRead,
    TaskUpdate,
    Project,
    Employee,
    User,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def update_project_task_counts(session: AsyncSession, project_id: int):
    # Count total tasks
    total_result = await session.execute(
        select(func.count(Task.id)).where(col(Task.project_id) == project_id)
    )
    total_tasks = total_result.scalar() or 0

    # Count completed tasks
    completed_result = await session.execute(
        select(func.count(Task.id)).where(col(Task.project_id) == project_id, col(Task.completed) == True)
    )
    completed_tasks = completed_result.scalar() or 0

    # Update project
    project = await session.get(Project, project_id)
    if project:
        project.total_tasks = total_tasks
        project.completed_tasks = completed_tasks
        session.add(project)


@router.post("/", response_model=TaskRead)
async def create_task(
    *, 
    session: AsyncSession = Depends(get_session), 
    task: TaskCreate,
    current_user: User = Depends(current_active_user)
):
    # Verify project exists and belongs to user's tenant
    db_project = await session.get(Project, task.project_id)
    if not db_project or db_project.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify employee exists and belongs to user's tenant if provided
    if task.employee_id is not None:
        db_employee = await session.get(Employee, task.employee_id)
        if not db_employee or db_employee.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail="Employee not found")

    db_task = Task.model_validate(task, update={"tenant_id": current_user.tenant_id})
    session.add(db_task)
    try:
        await session.flush()
        # Update project task count metrics in the same transaction
        await update_project_task_counts(session, db_task.project_id)
        await session.commit()
        await session.refresh(db_task)
        return db_task
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[TaskRead])
async def read_tasks(
    *, 
    session: AsyncSession = Depends(get_session),
    project_id: Optional[int] = Query(None),
    employee_id: Optional[int] = Query(None),
    completed: Optional[bool] = Query(None),
    current_user: User = Depends(current_active_user)
):
    query = select(Task).where(col(Task.tenant_id) == current_user.tenant_id)
    if project_id is not None:
        query = query.where(col(Task.project_id) == project_id)
    if employee_id is not None:
        query = query.where(col(Task.employee_id) == employee_id)
    if completed is not None:
        query = query.where(col(Task.completed) == completed)

    result = await session.execute(query)
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}", response_model=TaskRead)
async def read_task(
    *, 
    session: AsyncSession = Depends(get_session), 
    task_id: int,
    current_user: User = Depends(current_active_user)
):
    task = await session.get(Task, task_id)
    if not task or task.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskRead)
async def update_task(
    *, 
    session: AsyncSession = Depends(get_session), 
    task_id: int, 
    task_update: TaskUpdate,
    current_user: User = Depends(current_active_user)
):
    db_task = await session.get(Task, task_id)
    if not db_task or db_task.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Task not found")

    old_project_id = db_task.project_id
    task_data = task_update.model_dump(exclude_unset=True)

    # Validate project update if specified
    if "project_id" in task_data and task_data["project_id"] != old_project_id:
        new_project_id = task_data["project_id"]
        db_project = await session.get(Project, new_project_id)
        if not db_project or db_project.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail="Project not found")

    # Validate employee update if specified
    if "employee_id" in task_data and task_data["employee_id"] is not None:
        db_employee = await session.get(Employee, task_data["employee_id"])
        if not db_employee or db_employee.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail="Employee not found")

    # Update fields
    for key, value in task_data.items():
        setattr(db_task, key, value)
    db_task.updated_at = datetime.utcnow()

    session.add(db_task)
    try:
        await session.flush()
        # Update metrics for the projects in the same transaction
        await update_project_task_counts(session, old_project_id)
        if db_task.project_id != old_project_id:
            await update_project_task_counts(session, db_task.project_id)
        await session.commit()
        await session.refresh(db_task)
        return db_task
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{task_id}")
async def delete_task(
    *, 
    session: AsyncSession = Depends(get_session), 
    task_id: int,
    current_user: User = Depends(current_active_user)
):
    db_task = await session.get(Task, task_id)
    if not db_task or db_task.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Task not found")

    project_id = db_task.project_id
    await session.delete(db_task)
    try:
        await session.flush()
        # Recalculate metrics for the project in the same transaction
        await update_project_task_counts(session, project_id)
        await session.commit()
        return {"ok": True}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
