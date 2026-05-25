from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, SQLModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import (
    Employee,
    EmployeeCreate,
    EmployeeRead,
    EmployeeUpdate,
    EmployeeSkillLink,
    Skill,
    SkillWithFactor,
    EmployeeReadWithSkills,
)

router = APIRouter(prefix="/employees", tags=["employees"])


class EmployeeSkillAssign(SQLModel):
    skill_id: int
    factor: Optional[str] = None


@router.post("/", response_model=EmployeeRead)
async def create_employee(*, session: AsyncSession = Depends(get_session), employee: EmployeeCreate):
    db_employee = Employee.model_validate(employee)
    session.add(db_employee)
    try:
        await session.commit()
        await session.refresh(db_employee)
        return db_employee
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[EmployeeRead])
async def read_employees(*, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Employee))
    employees = result.scalars().all()
    return employees


@router.get("/{employee_id}", response_model=EmployeeReadWithSkills)
async def read_employee(*, session: AsyncSession = Depends(get_session), employee_id: int):
    # Eager load skills
    result = await session.execute(
        select(Employee).where(Employee.id == employee_id).options(selectinload(Employee.skills))
    )
    employee = result.scalar_one_or_none()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Fetch factors for the skills
    link_result = await session.execute(
        select(EmployeeSkillLink).where(EmployeeSkillLink.employee_id == employee_id)
    )
    links = link_result.scalars().all()
    factor_map = {link.skill_id: link.factor for link in links}

    # Construct the response
    employee_dict = employee.model_dump()
    skills_with_factor = []
    for skill in employee.skills:
        skill_dict = skill.model_dump()
        skill_dict["factor"] = factor_map.get(skill.id)
        skills_with_factor.append(SkillWithFactor(**skill_dict))
    
    return EmployeeReadWithSkills(**employee_dict, skills=skills_with_factor)


@router.put("/{employee_id}", response_model=EmployeeRead)
async def update_employee(
    *, session: AsyncSession = Depends(get_session), employee_id: int, employee: EmployeeUpdate
):
    db_employee = await session.get(Employee, employee_id)
    if not db_employee:
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
async def delete_employee(*, session: AsyncSession = Depends(get_session), employee_id: int):
    db_employee = await session.get(Employee, employee_id)
    if not db_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    await session.delete(db_employee)
    await session.commit()
    return {"ok": True}


@router.post("/{employee_id}/skills")
async def assign_skills_to_employee(
    *, session: AsyncSession = Depends(get_session), employee_id: int, skills: List[EmployeeSkillAssign]
):
    db_employee = await session.get(Employee, employee_id)
    if not db_employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Remove existing skills (or just specific ones, here we do full sync for simplicity)
    existing_links_result = await session.execute(
        select(EmployeeSkillLink).where(EmployeeSkillLink.employee_id == employee_id)
    )
    existing_links = existing_links_result.scalars().all()
    for link in existing_links:
        await session.delete(link)

    # Validate and add new skills
    for s in skills:
        db_skill = await session.get(Skill, s.skill_id)
        if not db_skill:
            raise HTTPException(status_code=404, detail=f"Skill {s.skill_id} not found")
            
        new_link = EmployeeSkillLink(employee_id=employee_id, skill_id=s.skill_id, factor=s.factor)
        session.add(new_link)

    try:
        await session.commit()
        return {"ok": True, "message": f"Skills updated for employee {employee_id}"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
