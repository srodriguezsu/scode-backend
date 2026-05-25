import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel

from app.main import app
from app.database import get_session

# Use in-memory SQLite for testing
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
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield

@pytest.fixture
async def session():
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture
async def unauth_client(session: AsyncSession):
    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
        
    app.dependency_overrides.clear()

async def get_authenticated_client(unauth_client: AsyncClient, email: str, password: str, tenant_id: str = None):
    # Register
    payload = {"email": email, "password": password}
    if tenant_id:
        payload["tenant_id"] = tenant_id
    await unauth_client.post("/auth/register", json=payload)
    
    # Login
    login_resp = await unauth_client.post(
        "/auth/jwt/login", 
        data={"username": email, "password": password}
    )
    token = login_resp.json()["access_token"]
    
    # Create authenticated client
    transport = ASGITransport(app=app)
    client = AsyncClient(
        transport=transport, 
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"}
    )
    return client

@pytest.fixture
async def auth_client(unauth_client: AsyncClient):
    client = await get_authenticated_client(unauth_client, "user1@example.com", "password", "tenant_a")
    yield client
    await client.aclose()

@pytest.fixture
async def auth_client_2(unauth_client: AsyncClient):
    client = await get_authenticated_client(unauth_client, "user2@example.com", "password", "tenant_b")
    yield client
    await client.aclose()
