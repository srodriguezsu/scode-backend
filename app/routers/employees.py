from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, SQLModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.auth import current_active_user
from app.models import (
    Employee,
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
    EmployeeSkillLink,
    Skill,
    SkillWithFactor,
    EmployeeReadWithSkills,
    User,
)

router = APIRouter(prefix="/employees", tags=["employees"])


class EmployeeSkillAssign(SQLModel):
    skill_id: int
    factor: Optional[str] = None


@router.post("/", response_model=EmployeeRead)
async def create_employee(
    *, 
    session: AsyncSession = Depends(get_session), 
    employee: EmployeeCreate,
    current_user: User = Depends(current_active_user)
):
    # Inject Multi-Tenancy: Force tenant_id to be the current user's tenant
    db_employee = Employee.model_validate(employee, update={"tenant_id": current_user.tenant_id})
    
    session.add(db_employee)
    try:
        await session.commit()
        await session.refresh(db_employee)
        return db_employee
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[EmployeeRead])
async def read_employees(
    *, 
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(current_active_user)
):
    # List Endpoint: Query only records matching the tenant_id
    result = await session.execute(
        select(Employee).where(Employee.tenant_id == current_user.tenant_id)
    )
    employees = result.scalars().all()
    return employees


@router.get("/{employee_id}", response_model=EmployeeReadWithSkills)
async def read_employee(
    *, 
    session: AsyncSession = Depends(get_session), 
    employee_id: int,
    current_user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Employee)
        .where(Employee.id == employee_id, Employee.tenant_id == current_user.tenant_id)
        .options(selectinload(Employee.skills))
    )
    employee = result.scalar_one_or_none()
    
    # Boundary Check: Return 404 if not found or belongs to another tenant
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    link_result = await session.execute(
        select(EmployeeSkillLink).where(EmployeeSkillLink.employee_id == employee_id)
    )
    links = link_result.scalars().all()
    factor_map = {link.skill_id: link.factor for link in links}

    employee_dict = employee.model_dump()
    skills_with_factor = []
    for skill in employee.skills:
        skill_dict = skill.model_dump()
        skill_dict["factor"] = factor_map.get(skill.id)
        skills_with_factor.append(SkillWithFactor(**skill_dict))
    
    return EmployeeReadWithSkills(**employee_dict, skills=skills_with_factor)


@router.put("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    *, 
    session: AsyncSession = Depends(get_session), 
    employee_id: int, 
    employee: EmployeeUpdate,
    current_user: User = Depends(current_active_user)
):
    db_employee = await session.get(Employee, employee_id)
    if not db_employee or db_employee.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    employee_data = employee.model_dump(exclude_unset=True)
    for key, value in employee_data.items():
        setattr(db_employee, key, value)
        
    session.add(db_employee)
    try:
        await session.commit()
        await session.refresh(db_employee)
        return db_employee
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{employee_id}")
async def delete_employee(
    *, 
    session: AsyncSession = Depends(get_session), 
    employee_id: int,
    current_user: User = Depends(current_active_user)
):
    db_employee = await session.get(Employee, employee_id)
    if not db_employee or db_employee.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    await session.delete(db_employee)
    await session.commit()
    return {"ok": True}


@router.post("/{employee_id}/skills")
async def assign_skills_to_employee(
    *, 
    session: AsyncSession = Depends(get_session), 
    employee_id: int, 
    skills: List[EmployeeSkillAssign],
    current_user: User = Depends(current_active_user)
):
    db_employee = await session.get(Employee, employee_id)
    if not db_employee or db_employee.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Employee not found")

    existing_links_result = await session.execute(
        select(EmployeeSkillLink).where(EmployeeSkillLink.employee_id == employee_id)
    )
    existing_links = existing_links_result.scalars().all()
    for link in existing_links:
        await session.delete(link)

    for s in skills:
        db_skill = await session.get(Skill, s.skill_id)
        if not db_skill or db_skill.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail=f"Skill {s.skill_id} not found in your tenant")
            
        new_link = EmployeeSkillLink(employee_id=employee_id, skill_id=s.skill_id, factor=s.factor)
        session.add(new_link)

    try:
        await session.commit()
        return {"ok": True, "message": f"Skills updated for employee {employee_id}"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
