from datetime import datetime
from enum import Enum as PyEnum
from typing import List, Optional
from sqlmodel import Field, Relationship, SQLModel, Column, String, Enum


class SkillType(str, PyEnum):
    hard = "hard"
    soft = "soft"


class FactorType(str, PyEnum):
    numeric = "numeric"
    categorical = "categorical"


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


class SkillBase(SQLModel):
    name: str = Field(sa_column=Column(String(255), unique=True, nullable=False))
    type: Optional[SkillType] = Field(sa_column=Column(Enum(SkillType)))
    factor_type: Optional[FactorType] = Field(sa_column=Column(Enum(FactorType)))


class Skill(SkillBase, table=True):
    __tablename__ = "skills"
    id: Optional[int] = Field(default=None, primary_key=True)

    employees: List["Employee"] = Relationship(back_populates="skills", link_model=EmployeeSkillLink)
    projects: List["Project"] = Relationship(back_populates="skills", link_model=ProjectSkillLink)


class SkillCreate(SkillBase):
    pass


class SkillRead(SkillBase):
    id: int


class EmployeeBase(SQLModel):
    national_id: str = Field(sa_column=Column(String(15), unique=True, nullable=False))
    name: Optional[str] = None
    last_name: Optional[str] = None


class Employee(EmployeeBase, table=True):
    __tablename__ = "employees"
    id: Optional[int] = Field(default=None, primary_key=True)

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


class ProjectBase(SQLModel):
    name: Optional[str] = Field(default=None, max_length=50)
    description: Optional[str] = Field(default=None, max_length=255)
    max_teams: Optional[int] = None
    min_team_size: Optional[int] = None
    max_team_size: Optional[int] = None


class Project(ProjectBase, table=True):
    __tablename__ = "projects"
    id: Optional[int] = Field(default=None, primary_key=True)
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
    created_at: datetime
    updated_at: datetime


class TeamBase(SQLModel):
    project_id: int = Field(foreign_key="projects.id", nullable=False)


class Team(TeamBase, table=True):
    __tablename__ = "teams"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    project: Project = Relationship(back_populates="teams")
    members: List[Employee] = Relationship(back_populates="teams", link_model=TeamMemberLink)


class TeamCreate(TeamBase):
    pass


class TeamRead(TeamBase):
    id: int
    created_at: datetime


# Enhanced schemas with relationships for nested read responses
class SkillWithFactor(SkillRead):
    factor: Optional[str] = None


class EmployeeReadWithSkills(EmployeeRead):
    skills: List[SkillWithFactor] = []


class ProjectReadWithSkills(ProjectRead):
    skills: List[SkillRead] = []


class TeamReadWithMembers(TeamRead):
    members: List[EmployeeRead] = []
