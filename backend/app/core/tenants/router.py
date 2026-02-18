import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenants import service
from app.core.tenants.schemas import TenantCreate, TenantRead, TenantUpdate
from app.dependencies import get_db, require_superadmin

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("/", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(data: TenantCreate, db: AsyncSession = Depends(get_db), _: None = Depends(require_superadmin)):
    if await service.get_tenant_by_slug(db, data.slug):
        raise HTTPException(status_code=409, detail="Slug already in use")
    return await service.create_tenant(db, data)


@router.get("/", response_model=list[TenantRead])
async def list_tenants(db: AsyncSession = Depends(get_db), _: None = Depends(require_superadmin)):
    return await service.list_tenants(db)


@router.get("/{tenant_id}", response_model=TenantRead)
async def get_tenant(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: None = Depends(require_superadmin)):
    tenant = await service.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.patch("/{tenant_id}", response_model=TenantRead)
async def update_tenant(tenant_id: uuid.UUID, data: TenantUpdate, db: AsyncSession = Depends(get_db), _: None = Depends(require_superadmin)):
    tenant = await service.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return await service.update_tenant(db, tenant, data)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(tenant_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: None = Depends(require_superadmin)):
    tenant = await service.get_tenant(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    await service.delete_tenant(db, tenant)
