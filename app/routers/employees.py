from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select, SQLModel
from sqlalchemy import func
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
    TeamMemberLink,
    Skill,
    SkillWithFactor,
    EmployeeReadWithSkills,
    User,
    SkillType,
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


@router.get("/", response_model=List[EmployeeReadWithSkills])
async def read_employees(
    *, 
    session: AsyncSession = Depends(get_session),
    skill_ids: Optional[List[str]] = Query(None),
    hard_skills_ids: Optional[List[str]] = Query(None),
    soft_skills_ids: Optional[List[str]] = Query(None),
    match_all: bool = Query(True),
    current_user: User = Depends(current_active_user)
):
    # List Endpoint: Query only records matching the tenant_id
    query = (
        select(Employee)
        .where(Employee.tenant_id == current_user.tenant_id)
        .options(selectinload(Employee.skills))
    )

    # Process and parse hard skill IDs (supporting both ?skill_ids=1&skill_ids=2 and ?skill_ids=1,2)
    raw_hard_ids = []
    if skill_ids:
        raw_hard_ids.extend(skill_ids)
    if hard_skills_ids:
        raw_hard_ids.extend(hard_skills_ids)

    actual_hard_ids = []
    for item in raw_hard_ids:
        for part in item.split(","):
            part = part.strip()
            if part.isdigit():
                actual_hard_ids.append(int(part))

    # Process and parse soft skill IDs
    raw_soft_ids = []
    if soft_skills_ids:
        raw_soft_ids.extend(soft_skills_ids)

    actual_soft_ids = []
    for item in raw_soft_ids:
        for part in item.split(","):
            part = part.strip()
            if part.isdigit():
                actual_soft_ids.append(int(part))

    if actual_hard_ids or actual_soft_ids:
        valid_skill_ids = []
        total_requested_count = len(set(actual_hard_ids)) + len(set(actual_soft_ids))

        # Validate hard skills
        if actual_hard_ids:
            hard_skills_query = await session.execute(
                select(Skill.id)
                .where(Skill.id.in_(actual_hard_ids))
                .where(Skill.tenant_id == current_user.tenant_id)
                .where(Skill.type == SkillType.hard)
            )
            valid_hard_ids = hard_skills_query.scalars().all()
            valid_skill_ids.extend(valid_hard_ids)

        # Validate soft skills
        if actual_soft_ids:
            soft_skills_query = await session.execute(
                select(Skill.id)
                .where(Skill.id.in_(actual_soft_ids))
                .where(Skill.tenant_id == current_user.tenant_id)
                .where(Skill.type == SkillType.soft)
            )
            valid_soft_ids = soft_skills_query.scalars().all()
            valid_skill_ids.extend(valid_soft_ids)

        # If match_all is True but some requested skill IDs are not valid for their respective type/tenant,
        # no employee can possess all of them.
        if match_all and len(valid_skill_ids) != total_requested_count:
            return []

        if not valid_skill_ids:
            # If match_all is False and none of the IDs are valid for their respective type, return no employees
            return []

        if match_all:
            # Must possess ALL specified skills
            subquery = (
                select(EmployeeSkillLink.employee_id)
                .where(EmployeeSkillLink.skill_id.in_(valid_skill_ids))
                .group_by(EmployeeSkillLink.employee_id)
                .having(func.count(EmployeeSkillLink.skill_id.distinct()) == len(valid_skill_ids))
            )
            query = query.where(Employee.id.in_(subquery))
        else:
            # Must possess ANY of the specified skills
            subquery = (
                select(EmployeeSkillLink.employee_id)
                .where(EmployeeSkillLink.skill_id.in_(valid_skill_ids))
            )
            query = query.where(Employee.id.in_(subquery))

    result = await session.execute(query)
    employees = result.scalars().all()

    if not employees:
        return []

    employee_ids = [e.id for e in employees]
    link_result = await session.execute(
        select(EmployeeSkillLink).where(EmployeeSkillLink.employee_id.in_(employee_ids))
    )
    links = link_result.scalars().all()
    factor_map = {(link.employee_id, link.skill_id): link.factor for link in links}
    
    response = []
    for emp in employees:
        emp_dict = emp.model_dump()
        skills_with_factor = []
        for skill in emp.skills:
            skill_dict = skill.model_dump()
            skill_dict["factor"] = factor_map.get((emp.id, skill.id))
            skills_with_factor.append(SkillWithFactor(**skill_dict))
        response.append(EmployeeReadWithSkills(**emp_dict, skills=skills_with_factor))
        
    return response


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
        
    skill_links = await session.execute(
        select(EmployeeSkillLink).where(EmployeeSkillLink.employee_id == employee_id)
    )
    for link in skill_links.scalars().all():
        await session.delete(link)
        
    team_links = await session.execute(
        select(TeamMemberLink).where(TeamMemberLink.employee_id == employee_id)
    )
    for link in team_links.scalars().all():
        await session.delete(link)

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
