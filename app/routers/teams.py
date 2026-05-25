from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select, SQLModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import (
    Team,
    TeamCreate,
    TeamRead,
    TeamMemberLink,
    Employee,
    TeamReadWithMembers,
    Project,
)

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamMemberAssign(SQLModel):
    employee_id: int


@router.post("/", response_model=TeamRead)
async def create_team(*, session: AsyncSession = Depends(get_session), team: TeamCreate):
    # Verify the project exists
    project = await session.get(Project, team.project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project {team.project_id} not found")

    # Optionally, we could check if max_teams limit for the project has been reached here.
    
    db_team = Team.model_validate(team)
    session.add(db_team)
    try:
        await session.commit()
        await session.refresh(db_team)
        return db_team
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{team_id}", response_model=TeamReadWithMembers)
async def read_team(*, session: AsyncSession = Depends(get_session), team_id: int):
    result = await session.execute(
        select(Team).where(Team.id == team_id).options(selectinload(Team.members))
    )
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.post("/{team_id}/members")
async def add_members_to_team(
    *, session: AsyncSession = Depends(get_session), team_id: int, members: List[TeamMemberAssign]
):
    db_team = await session.get(Team, team_id)
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")
        
    # Get the project to check max_team_size constraints if any
    project = await session.get(Project, db_team.project_id)
    
    # We won't strictly enforce sizes unless all logic is present, but this is where it'd go.

    # Remove existing members (doing full sync for simplicity)
    existing_links_result = await session.execute(
        select(TeamMemberLink).where(TeamMemberLink.team_id == team_id)
    )
    existing_links = existing_links_result.scalars().all()
    for link in existing_links:
        await session.delete(link)

    # Validate and add new members
    for m in members:
        db_employee = await session.get(Employee, m.employee_id)
        if not db_employee:
            raise HTTPException(status_code=404, detail=f"Employee {m.employee_id} not found")
            
        new_link = TeamMemberLink(team_id=team_id, employee_id=m.employee_id)
        session.add(new_link)

    try:
        await session.commit()
        return {"ok": True, "message": f"Members updated for team {team_id}"}
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
