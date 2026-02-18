import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.models import RefreshToken
from app.core.auth.security import create_access_token, generate_refresh_token, hash_refresh_token, verify_password
from app.core.rbac.models import User
from app.core.tenants.service import get_tenant_by_slug
from app.settings import get_settings

settings = get_settings()


class AuthResult:
    def __init__(self, access_token: str, refresh_token: str):
        self.access_token = access_token
        self.refresh_token = refresh_token


class LocalAuthProvider:
    async def login(self, db: AsyncSession, email: str, password: str, tenant_slug: str) -> AuthResult:
        tenant = await get_tenant_by_slug(db, tenant_slug)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")

        result = await db.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == email.lower(), User.is_deleted == False)
        )
        user: User | None = result.scalar_one_or_none()

        if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if user.status != "active":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account suspended")

        access_token = create_access_token(user.id, tenant.id)
        raw_refresh, refresh_hash = generate_refresh_token()

        db.add(RefreshToken(
            tenant_id=tenant.id,
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        ))
        await db.flush()
        return AuthResult(access_token=access_token, refresh_token=raw_refresh)


_provider = LocalAuthProvider()


def get_auth_provider() -> LocalAuthProvider:
    return _provider


async def refresh_tokens(db: AsyncSession, raw_token: str) -> AuthResult:
    token_hash = hash_refresh_token(raw_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    db_token: RefreshToken | None = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)
    if not db_token or db_token.revoked_at is not None or db_token.expires_at.replace(tzinfo=timezone.utc) < now:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    db_token.revoked_at = now
    access_token = create_access_token(db_token.user_id, db_token.tenant_id)
    raw_new, new_hash = generate_refresh_token()

    db.add(RefreshToken(
        tenant_id=db_token.tenant_id,
        user_id=db_token.user_id,
        token_hash=new_hash,
        expires_at=now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    ))
    await db.flush()
    return AuthResult(access_token=access_token, refresh_token=raw_new)


async def logout(db: AsyncSession, raw_token: str) -> None:
    token_hash = hash_refresh_token(raw_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    db_token: RefreshToken | None = result.scalar_one_or_none()
    if db_token and db_token.revoked_at is None:
        db_token.revoked_at = datetime.now(timezone.utc)
        await db.flush()
