from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.auth import current_active_user
from app.models import (
    Skill,
    SkillCreate,
    SkillRead,
    SkillUpdate,
    User,
    EmployeeSkillLink,
    Employee,
    ProjectSkillLink,
    SkillType,
)

router = APIRouter(prefix="/skills", tags=["skills"])


@router.post("/", response_model=SkillRead)
async def create_skill(
    *, 
    session: AsyncSession = Depends(get_session), 
    skill: SkillCreate,
    current_user: User = Depends(current_active_user)
):
    db_skill = Skill.model_validate(skill, update={"tenant_id": current_user.tenant_id})
    
    session.add(db_skill)
    try:
        await session.commit()
        await session.refresh(db_skill)
        return db_skill
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[SkillRead])
async def read_skills(
    *, 
    session: AsyncSession = Depends(get_session),
    type: Optional[SkillType] = Query(None, description="Filter skills by type ('hard' or 'soft')"),
    current_user: User = Depends(current_active_user)
):
    query = select(Skill).where(Skill.tenant_id == current_user.tenant_id)
    if type:
        query = query.where(Skill.type == type)
        
    result = await session.execute(query)
    skills = result.scalars().all()
    return skills


@router.get("/{skill_id}", response_model=SkillRead)
async def read_skill(
    *, 
    session: AsyncSession = Depends(get_session), 
    skill_id: int,
    current_user: User = Depends(current_active_user)
):
    skill = await session.get(Skill, skill_id)
    if not skill or skill.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.delete("/{skill_id}")
async def delete_skill(
    *, 
    session: AsyncSession = Depends(get_session), 
    skill_id: int,
    current_user: User = Depends(current_active_user)
):
    skill = await session.get(Skill, skill_id)
    if not skill or skill.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Skill not found")
        
    emp_links = await session.execute(
        select(EmployeeSkillLink).where(EmployeeSkillLink.skill_id == skill_id)
    )
    for link in emp_links.scalars().all():
        await session.delete(link)
        
    proj_links = await session.execute(
        select(ProjectSkillLink).where(ProjectSkillLink.skill_id == skill_id)
    )
    for link in proj_links.scalars().all():
        await session.delete(link)

    await session.delete(skill)
    await session.commit()
    return {"ok": True}

@router.patch("/{skill_id}", response_model=SkillRead)
async def update_skill(
    *,
    session: AsyncSession = Depends(get_session),
    skill_id: int,
    skill_update: SkillUpdate,
    current_user: User = Depends(current_active_user)
):
    skill = await session.get(Skill, skill_id)
    if not skill or skill.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    skill_data = skill_update.model_dump(exclude_unset=True)
    for key, value in skill_data.items():
        setattr(skill, key, value)
        
    session.add(skill)
    try:
        await session.commit()
        await session.refresh(skill)
        return skill
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{skill_id}/factors", response_model=List[str])
async def read_skill_factors(
    *,
    session: AsyncSession = Depends(get_session),
    skill_id: int,
    current_user: User = Depends(current_active_user)
):
    skill = await session.get(Skill, skill_id)
    if not skill or skill.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Skill not found")
        
    result = await session.execute(
        select(EmployeeSkillLink.factor)
        .join(Employee, Employee.id == EmployeeSkillLink.employee_id)
        .where(
            EmployeeSkillLink.skill_id == skill_id,
            Employee.tenant_id == current_user.tenant_id,
            EmployeeSkillLink.factor.isnot(None)
        )
        .distinct()
    )
    factors = result.scalars().all()
    return factors
