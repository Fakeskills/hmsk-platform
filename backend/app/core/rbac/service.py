import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac.models import User, Role, UserRoleAssignment
from app.core.rbac.schemas import UserCreate, UserUpdate, RoleCreate
from app.core.auth.security import hash_password


async def create_user(db: AsyncSession, tenant_id: uuid.UUID, data: UserCreate) -> User:
    user = User(tenant_id=tenant_id, email=data.email.lower(), hashed_password=hash_password(data.password), full_name=data.full_name)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def get_user(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id, User.is_deleted == False))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, tenant_id: uuid.UUID, email: str) -> User | None:
    result = await db.execute(select(User).where(User.tenant_id == tenant_id, User.email == email.lower(), User.is_deleted == False))
    return result.scalar_one_or_none()


async def list_users(db: AsyncSession, tenant_id: uuid.UUID) -> list[User]:
    result = await db.execute(select(User).where(User.tenant_id == tenant_id, User.is_deleted == False))
    return list(result.scalars().all())


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user)
    return user


async def delete_user(db: AsyncSession, user: User) -> None:
    user.is_deleted = True
    await db.flush()


async def create_role(db: AsyncSession, tenant_id: uuid.UUID, data: RoleCreate) -> Role:
    role = Role(tenant_id=tenant_id, **data.model_dump())
    db.add(role)
    await db.flush()
    await db.refresh(role)
    return role


async def list_roles(db: AsyncSession, tenant_id: uuid.UUID) -> list[Role]:
    result = await db.execute(select(Role).where(Role.tenant_id == tenant_id, Role.is_deleted == False))
    return list(result.scalars().all())


async def assign_role(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, role_id: uuid.UUID) -> UserRoleAssignment:
    assignment = UserRoleAssignment(tenant_id=tenant_id, user_id=user_id, role_id=role_id)
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)
    return assignment


async def revoke_role(db: AsyncSession, tenant_id: uuid.UUID, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
    result = await db.execute(select(UserRoleAssignment).where(UserRoleAssignment.tenant_id == tenant_id, UserRoleAssignment.user_id == user_id, UserRoleAssignment.role_id == role_id))
    assignment = result.scalar_one_or_none()
    if not assignment:
        return False
    await db.delete(assignment)
    await db.flush()
    return True
