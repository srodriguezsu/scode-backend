from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import SQLModel

from app.database import engine
from app.routers import employees, projects, teams, skills


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the database tables
    async with engine.begin() as conn:
        # Avoid dropping tables in production, just creating missing ones for MVP
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # Cleanup on shutdown if necessary
    await engine.dispose()


app = FastAPI(
    title="Employee Skill Matrix API",
    description="REST API backend for grouping employees into optimized project teams.",
    version="1.0.0",
    lifespan=lifespan,
)

# Include routers
app.include_router(skills.router)
app.include_router(employees.router)
app.include_router(projects.router)
app.include_router(teams.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Welcome to the Employee Skill Matrix API"}
