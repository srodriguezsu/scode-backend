from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.auth import current_active_user
from app.models import Skill, SkillCreate, SkillRead, SkillUpdate, User

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
    current_user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Skill).where(Skill.tenant_id == current_user.tenant_id)
    )
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
