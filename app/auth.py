import uuid
from typing import Optional
from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import User, UserCreate

# SECRET should ideally be imported from environment settings
SECRET = "my-super-secret-jwt-key"

# Database Adapter
async def get_user_db(session: AsyncSession = Depends(get_session)):
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = SECRET
    verification_token_secret = SECRET

    async def on_after_register(self, user: User, request: Optional[any] = None):
        print(f"User {user.id} has registered to tenant {user.tenant_id}.")

    async def create(
        self,
        user_create: UserCreate,
        safe: bool = False,
        request: Optional[any] = None,
    ) -> User:
        # Dynamically generate a fresh UUID for the tenant if none is provided
        if not user_create.tenant_id:
            user_create.tenant_id = str(uuid.uuid4())
        return await super().create(user_create, safe=safe, request=request)


async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)


# JWT Strategy and Transport setup
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=SECRET, lifetime_seconds=3600)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](
    get_user_manager,
    [auth_backend],
)

# Current Active User Dependency
current_active_user = fastapi_users.current_user(active=True)
