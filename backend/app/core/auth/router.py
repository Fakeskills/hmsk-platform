from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import service as auth_service
from app.core.auth.schemas import LoginRequest, TokenResponse, RefreshRequest, LogoutRequest
from app.core.rbac.schemas import UserRead
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    provider = auth_service.get_auth_provider()
    result = await provider.login(db, body.email, body.password, body.tenant_slug)
    return TokenResponse(access_token=result.access_token, refresh_token=result.refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    result = await auth_service.refresh_tokens(db, body.refresh_token)
    return TokenResponse(access_token=result.access_token, refresh_token=result.refresh_token)


@router.post("/logout", status_code=204)
async def logout(body: LogoutRequest, db: AsyncSession = Depends(get_db)):
    await auth_service.logout(db, body.refresh_token)


@router.get("/me", response_model=UserRead)
async def me(current: CurrentUser = Depends(get_current_user)):
    return current.user
