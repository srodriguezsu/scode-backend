import os
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Normally this would be loaded via pydantic-settings
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mysql+aiomysql://root:password@localhost/skill_matrix"
)

# Create the async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,         # Ensure this is False in production to save Cloud Run log overhead
    future=True,        # Keep if using SQLAlchemy 1.4; remove if on 2.0+
    poolclass=NullPool  # <--- This is the fix. Disables pooling entirely.
)

# Async session factory
async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session() -> AsyncSession: # type: ignore
    """
    FastAPI dependency to yield an async database session.
    """
    async with async_session_maker() as session:
        yield session
