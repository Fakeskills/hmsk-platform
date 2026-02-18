import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenants.models import Tenant
from app.core.tenants.schemas import TenantCreate, TenantUpdate


async def create_tenant(db: AsyncSession, data: TenantCreate) -> Tenant:
    tenant = Tenant(**data.model_dump())
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    return tenant


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id, Tenant.is_deleted == False))
    return result.scalar_one_or_none()


async def get_tenant_by_slug(db: AsyncSession, slug: str) -> Tenant | None:
    result = await db.execute(select(Tenant).where(Tenant.slug == slug, Tenant.is_deleted == False))
    return result.scalar_one_or_none()


async def list_tenants(db: AsyncSession) -> list[Tenant]:
    result = await db.execute(select(Tenant).where(Tenant.is_deleted == False))
    return list(result.scalars().all())


async def update_tenant(db: AsyncSession, tenant: Tenant, data: TenantUpdate) -> Tenant:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(tenant, field, value)
    await db.flush()
    await db.refresh(tenant)
    return tenant


async def delete_tenant(db: AsyncSession, tenant: Tenant) -> None:
    tenant.is_deleted = True
    await db.flush()
