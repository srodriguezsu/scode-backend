from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

load_dotenv()

from app.database import engine
from app.routers import employees, projects, teams, skills
from app.auth import fastapi_users, auth_backend
from app.models import UserRead, UserCreate, UserUpdate

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
    title="SCODE API",
    description="REST API backend for grouping employees into optimized project teams.",
    version="1.0.0",
    lifespan=lifespan,
)

cors_origins_str = os.getenv("CORS_ORIGINS", "*")

if cors_origins_str == "*":
    # The CORS specification doesn't allow `allow_origins=["*"]` with `allow_credentials=True`.
    # To allow any origin during development while keeping credentials, we use a regex that matches anything.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    cors_origins = [origin.strip() for origin in cors_origins_str.split(";") if origin.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include Auth Routers
app.include_router(
    fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# Include Resource Routers
app.include_router(skills.router)
app.include_router(employees.router)
app.include_router(projects.router)
app.include_router(teams.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "message": "Welcome to the SCODE API"}
