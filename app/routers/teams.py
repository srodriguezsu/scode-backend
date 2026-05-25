from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, SQLModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.auth import current_active_user
from app.models import (
    Team,
    TeamCreate,
    TeamRead,
    TeamMemberLink,
    Employee,
    TeamReadWithMembers,
    Project,
    User,
)

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamMemberAssign(SQLModel):
    employee_id: int


@router.post("/", response_model=TeamRead)
async def create_team(
    *, 
    session: AsyncSession = Depends(get_session), 
    team: TeamCreate,
    current_user: User = Depends(current_active_user)
):
    project = await session.get(Project, team.project_id)
    if not project or project.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail=f"Project {team.project_id} not found in your tenant")

    db_team = Team.model_validate(team, update={"tenant_id": current_user.tenant_id})
    
    session.add(db_team)
    try:
        await session.commit()
        await session.refresh(db_team)
        return db_team
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{team_id}", response_model=TeamReadWithMembers)
async def read_team(
    *, 
    session: AsyncSession = Depends(get_session), 
    team_id: int,
    current_user: User = Depends(current_active_user)
):
    result = await session.execute(
        select(Team)
        .where(Team.id == team_id, Team.tenant_id == current_user.tenant_id)
        .options(selectinload(Team.members))
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.post("/{team_id}/members")
async def add_members_to_team(
    *, 
    session: AsyncSession = Depends(get_session), 
    team_id: int, 
    members: List[TeamMemberAssign],
    current_user: User = Depends(current_active_user)
):
    db_team = await session.get(Team, team_id)
    if not db_team or db_team.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=404, detail="Team not found")

    existing_links_result = await session.execute(
        select(TeamMemberLink).where(TeamMemberLink.team_id == team_id)
    )
    existing_links = existing_links_result.scalars().all()
    for link in existing_links:
        await session.delete(link)

    for m in members:
        db_employee = await session.get(Employee, m.employee_id)
        if not db_employee or db_employee.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail=f"Employee {m.employee_id} not found in your tenant")
            
        new_link = TeamMemberLink(team_id=team_id, employee_id=m.employee_id)
        session.add(new_link)

    try:
        await session.commit()
        return {"ok": True, "message": f"Members updated for team {team_id}"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
