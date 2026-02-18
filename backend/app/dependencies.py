import uuid
from dataclasses import dataclass
from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.security import decode_access_token
from app.core.rbac.models import User
from app.core.rbac.service import get_user
from app.db.session import AsyncSessionLocal, set_rls_context

bearer = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user: User
    user_id: uuid.UUID
    tenant_id: uuid.UUID


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = uuid.UUID(payload["sub"])
    tenant_id = uuid.UUID(payload["tenant_id"])

    await set_rls_context(db, tenant_id, user_id)

    user = await get_user(db, user_id)
    if not user or user.is_deleted or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return CurrentUser(user=user, user_id=user_id, tenant_id=tenant_id)


async def require_superadmin(
    current: CurrentUser = Depends(get_current_user),
) -> None:
    if not current.user.is_superadmin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin required")
