import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import service
from app.core.rbac.schemas import RoleCreate, RoleRead, UserCreate, UserUpdate, UserRead, RoleAssignRequest, UserRoleAssignmentRead
from app.dependencies import get_db, get_current_user, CurrentUser

router = APIRouter(tags=["users & roles"])


@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(data: UserCreate, db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    if await service.get_user_by_email(db, current.tenant_id, data.email):
        raise HTTPException(409, "Email already registered in this tenant")
    return await service.create_user(db, current.tenant_id, data)


@router.get("/users", response_model=list[UserRead])
async def list_users(db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return await service.list_users(db, current.tenant_id)


@router.get("/users/{user_id}", response_model=UserRead)
async def get_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    user = await service.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.patch("/users/{user_id}", response_model=UserRead)
async def update_user(user_id: uuid.UUID, data: UserUpdate, db: AsyncSession = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    user = await service.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return await service.update_user(db, user, data)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: CurrentUser = Depends(get_current_user)):
    user = await service.get_user(db, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    await service.delete_user(db, user)


@router.post("/roles", response_model=RoleRead, status_code=201)
async def create_role(data: RoleCreate, db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return await service.create_role(db, current.tenant_id, data)


@router.get("/roles", response_model=list[RoleRead])
async def list_roles(db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return await service.list_roles(db, current.tenant_id)


@router.post("/users/{user_id}/roles", response_model=UserRoleAssignmentRead, status_code=201)
async def assign_role(user_id: uuid.UUID, body: RoleAssignRequest, db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    return await service.assign_role(db, current.tenant_id, user_id, body.role_id)


@router.delete("/users/{user_id}/roles/{role_id}", status_code=204)
async def revoke_role(user_id: uuid.UUID, role_id: uuid.UUID, db: AsyncSession = Depends(get_db), current: CurrentUser = Depends(get_current_user)):
    if not await service.revoke_role(db, current.tenant_id, user_id, role_id):
        raise HTTPException(404, "Assignment not found")
