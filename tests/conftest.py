import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from app.main import app
from app.database import get_session

# Use in-memory SQLite for testing. StaticPool is required to maintain the
# database in memory across connections.
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    # Setup the tables once for the test session
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    # We could drop tables here if it wasn't in-memory

@pytest.fixture
async def session():
    async with TestingSessionLocal() as session:
        yield session
        # Optionally rollback any uncommitted transactions or clear tables here

@pytest.fixture
async def client(session: AsyncSession):
    # Dependency override
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
        
    # Clear overrides
    app.dependency_overrides.clear()
