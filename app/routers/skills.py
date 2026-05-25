from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Skill, SkillCreate, SkillRead

router = APIRouter(prefix="/skills", tags=["skills"])


@router.post("/", response_model=SkillRead)
async def create_skill(*, session: AsyncSession = Depends(get_session), skill: SkillCreate):
    db_skill = Skill.model_validate(skill)
    session.add(db_skill)
    try:
        await session.commit()
        await session.refresh(db_skill)
        return db_skill
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[SkillRead])
async def read_skills(*, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Skill))
    skills = result.scalars().all()
    return skills


@router.get("/{skill_id}", response_model=SkillRead)
async def read_skill(*, session: AsyncSession = Depends(get_session), skill_id: int):
    skill = await session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.delete("/{skill_id}")
async def delete_skill(*, session: AsyncSession = Depends(get_session), skill_id: int):
    skill = await session.get(Skill, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    await session.delete(skill)
    await session.commit()
    return {"ok": True}
