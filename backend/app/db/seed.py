import asyncio
import os
import uuid

from sqlalchemy import select

from app.core.auth.security import hash_password
from app.core.rbac.models import User
from app.core.tenants.models import Tenant
from app.db.session import get_session


async def seed() -> None:
    tenant_name = os.getenv("SEED_TENANT_NAME", "HMSK Admin")
    tenant_slug = os.getenv("SEED_TENANT_SLUG", "hmsk-admin")
    admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@hmsk.local")
    admin_password = os.getenv("SEED_ADMIN_PASSWORD", "changeme123!")

    async with get_session() as db:
        existing = await db.execute(select(Tenant).where(Tenant.slug == tenant_slug))
        tenant = existing.scalar_one_or_none()

        if not tenant:
            tenant = Tenant(id=uuid.uuid4(), name=tenant_name, slug=tenant_slug, status="active")
            db.add(tenant)
            await db.flush()
            print(f"✅  Tenant: {tenant.slug} ({tenant.id})")
        else:
            print(f"⏭️   Tenant finnes: {tenant.slug}")

        existing_user = await db.execute(
            select(User).where(User.tenant_id == tenant.id, User.email == admin_email.lower())
        )
        user = existing_user.scalar_one_or_none()

        if not user:
            user = User(
                id=uuid.uuid4(),
                tenant_id=tenant.id,
                email=admin_email.lower(),
                hashed_password=hash_password(admin_password),
                full_name="HMSK Superadmin",
                is_superadmin=True,
            )
            db.add(user)
            await db.flush()
            print(f"✅  Superadmin: {user.email}")
        else:
            print(f"⏭️   Admin finnes: {user.email}")

    print("Ferdig.")


if __name__ == "__main__":
    asyncio.run(seed())
