from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, SQLModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import (
    Project,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    ProjectSkillLink,
    Skill,
    SkillType,
    Team,
    TeamReadWithMembers,
    ProjectReadWithSkills,
)

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectSkillAssign(SQLModel):
    skill_id: int


@router.post("/", response_model=ProjectRead)
async def create_project(*, session: AsyncSession = Depends(get_session), project: ProjectCreate):
    db_project = Project.model_validate(project)
    session.add(db_project)
    try:
        await session.commit()
        await session.refresh(db_project)
        return db_project
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", response_model=List[ProjectRead])
async def read_projects(*, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Project))
    projects = result.scalars().all()
    return projects


@router.get("/{project_id}", response_model=ProjectReadWithSkills)
async def read_project(*, session: AsyncSession = Depends(get_session), project_id: int):
    # Eager load skills
    result = await session.execute(
        select(Project).where(Project.id == project_id).options(selectinload(Project.skills))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    *, session: AsyncSession = Depends(get_session), project_id: int, project: ProjectUpdate
):
    db_project = await session.get(Project, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_data = project.model_dump(exclude_unset=True)
    for key, value in project_data.items():
        setattr(db_project, key, value)
        
    session.add(db_project)
    try:
        await session.commit()
        await session.refresh(db_project)
        return db_project
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{project_id}")
async def delete_project(*, session: AsyncSession = Depends(get_session), project_id: int):
    db_project = await session.get(Project, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    await session.delete(db_project)
    await session.commit()
    return {"ok": True}


@router.post("/{project_id}/skills")
async def assign_skills_to_project(
    *, session: AsyncSession = Depends(get_session), project_id: int, skills: List[ProjectSkillAssign]
):
    db_project = await session.get(Project, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Remove existing skills (or just specific ones, doing full sync for simplicity)
    existing_links_result = await session.execute(
        select(ProjectSkillLink).where(ProjectSkillLink.project_id == project_id)
    )
    existing_links = existing_links_result.scalars().all()
    for link in existing_links:
        await session.delete(link)

    # Validate and add new skills
    for s in skills:
        db_skill = await session.get(Skill, s.skill_id)
        if not db_skill:
            raise HTTPException(status_code=404, detail=f"Skill {s.skill_id} not found")
        
        # Verify that it is a hard skill (from DBML note)
        if db_skill.type != SkillType.hard:
            raise HTTPException(
                status_code=400, 
                detail=f"Skill {s.skill_id} ({db_skill.name}) is not a hard skill. Only hard skills can be attached to projects."
            )
            
        new_link = ProjectSkillLink(project_id=project_id, skill_id=s.skill_id)
        session.add(new_link)

    try:
        await session.commit()
        return {"ok": True, "message": f"Skills updated for project {project_id}"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/teams", response_model=List[TeamReadWithMembers])
async def read_project_teams(*, session: AsyncSession = Depends(get_session), project_id: int):
    db_project = await session.get(Project, project_id)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Fetch teams for this project and eager load their members
    result = await session.execute(
        select(Team)
        .where(Team.project_id == project_id)
        .options(selectinload(Team.members))
    )
    teams = result.scalars().all()
    
    return teams
