import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, Column, String, Enum
from fastapi_users import schemas


# --- Enums ---
class SkillType(str, PyEnum):
    hard = "hard"
    soft = "soft"

class FactorType(str, PyEnum):
    numeric = "numeric"
    categorical = "categorical"


# --- Link Tables ---
# (They inherit the tenant boundaries of their foreign keys, but adding tenant_id helps with isolation logic if needed. We'll leave them as pure link tables for simplicity, trusting the endpoints to enforce boundaries on the main entities.)
class TeamMemberLink(SQLModel, table=True):
    __tablename__ = "team_members"
    team_id: Optional[int] = Field(default=None, foreign_key="teams.id", primary_key=True)
    employee_id: Optional[int] = Field(default=None, foreign_key="employees.id", primary_key=True)

class EmployeeSkillLink(SQLModel, table=True):
    __tablename__ = "employee_skill"
    employee_id: Optional[int] = Field(default=None, foreign_key="employees.id", primary_key=True)
    skill_id: Optional[int] = Field(default=None, foreign_key="skills.id", primary_key=True)
    factor: Optional[str] = Field(default=None, max_length=10)

class ProjectSkillLink(SQLModel, table=True):
    __tablename__ = "project_skill"
    project_id: Optional[int] = Field(default=None, foreign_key="projects.id", primary_key=True)
    skill_id: Optional[int] = Field(default=None, foreign_key="skills.id", primary_key=True)


# --- Core Entities ---

class SkillBase(SQLModel):
    name: str = Field(sa_column=Column(String(255), nullable=False))
    type: Optional[SkillType] = Field(sa_column=Column(Enum(SkillType)))
    factor_type: Optional[FactorType] = Field(sa_column=Column(Enum(FactorType)))
    
class Skill(SkillBase, table=True):
    __tablename__ = "skills"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, nullable=False)

    employees: List["Employee"] = Relationship(back_populates="skills", link_model=EmployeeSkillLink)
    projects: List["Project"] = Relationship(back_populates="skills", link_model=ProjectSkillLink)

class SkillCreate(SkillBase):
    pass

class SkillRead(SkillBase):
    id: int
    tenant_id: str


class EmployeeBase(SQLModel):
    national_id: str = Field(sa_column=Column(String(15), nullable=False))
    name: Optional[str] = None
    last_name: Optional[str] = None

class Employee(EmployeeBase, table=True):
    __tablename__ = "employees"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, nullable=False)

    skills: List[Skill] = Relationship(back_populates="employees", link_model=EmployeeSkillLink)
    teams: List["Team"] = Relationship(back_populates="members", link_model=TeamMemberLink)

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(SQLModel):
    national_id: Optional[str] = None
    name: Optional[str] = None
    last_name: Optional[str] = None

class EmployeeRead(EmployeeBase):
    id: int
    tenant_id: str


class ProjectBase(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    max_teams: Optional[int] = None
    min_team_size: Optional[int] = None
    max_team_size: Optional[int] = None

class Project(ProjectBase, table=True):
    __tablename__ = "projects"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    teams: List["Team"] = Relationship(back_populates="project")
    skills: List[Skill] = Relationship(back_populates="projects", link_model=ProjectSkillLink)

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    max_teams: Optional[int] = None
    min_team_size: Optional[int] = None
    max_team_size: Optional[int] = None

class ProjectRead(ProjectBase):
    id: int
    tenant_id: str
    created_at: datetime
    updated_at: datetime


class TeamBase(SQLModel):
    project_id: int = Field(foreign_key="projects.id", nullable=False)

class Team(TeamBase, table=True):
    __tablename__ = "teams"
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    project: Project = Relationship(back_populates="teams")
    members: List[Employee] = Relationship(back_populates="teams", link_model=TeamMemberLink)

class TeamCreate(TeamBase):
    pass

class TeamRead(TeamBase):
    id: int
    tenant_id: str
    created_at: datetime


# Enhanced schemas with relationships
class SkillWithFactor(SkillRead):
    factor: Optional[str] = None

class EmployeeReadWithSkills(EmployeeRead):
    skills: List[SkillWithFactor] = []

class ProjectReadWithSkills(ProjectRead):
    skills: List[SkillRead] = []

class TeamReadWithMembers(TeamRead):
    members: List[EmployeeRead] = []


# --- Multi-Tenancy & Auth (User Model) ---

class User(SQLModel, table=True):
    __tablename__ = "user"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    is_superuser: bool = Field(default=False, nullable=False)
    is_verified: bool = Field(default=False, nullable=False)
    
    # Crucial Multi-tenant context
    tenant_id: str = Field(index=True, nullable=False)


class UserRead(schemas.BaseUser[uuid.UUID]):
    tenant_id: str

class UserCreate(schemas.BaseUserCreate):
    tenant_id: Optional[str] = None

class UserUpdate(schemas.BaseUserUpdate):
    tenant_id: Optional[str] = None
