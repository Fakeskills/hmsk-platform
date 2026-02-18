#!/usr/bin/env bash
# =============================================================================
# setup.sh – HMSK Platform Sprint 1
# Kjør fra roten av hmsk-platform-mappen din:
#   bash setup.sh
# =============================================================================
set -e

GITHUB_USER="fakeskills"
REPO_NAME="hmsk-platform"

echo "🚀  Setter opp HMSK Platform..."

# ── Mappestruktur ─────────────────────────────────────────────────────────────
mkdir -p \
  backend/app/core/auth \
  backend/app/core/tenants \
  backend/app/core/rbac \
  backend/app/core/audit \
  backend/app/db/migrations/versions \
  backend/app/db/rls \
  infra \
  tests

# ── Touch __init__.py filer ───────────────────────────────────────────────────
touch backend/app/__init__.py
touch backend/app/core/__init__.py
touch backend/app/core/auth/__init__.py
touch backend/app/core/tenants/__init__.py
touch backend/app/core/rbac/__init__.py
touch backend/app/core/audit/__init__.py
touch backend/app/db/__init__.py
touch tests/__init__.py

echo "📁  Mapper opprettet"

# =============================================================================
# FILER
# =============================================================================

# ── .gitignore ────────────────────────────────────────────────────────────────
cat > .gitignore << 'ENDOFFILE'
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.mypy_cache/
*.egg-info/
dist/
build/
.venv/
venv/
ENDOFFILE

# ── .env.example ──────────────────────────────────────────────────────────────
cat > .env.example << 'ENDOFFILE'
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=hmsk
POSTGRES_USER=hmsk
POSTGRES_PASSWORD=changeme
DATABASE_URL=postgresql+asyncpg://hmsk:changeme@postgres:5432/hmsk
DATABASE_SYNC_URL=postgresql+psycopg2://hmsk:changeme@postgres:5432/hmsk
JWT_SECRET=CHANGE_ME_32_CHARS_MINIMUM_SECRET
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
APP_ENV=development
APP_DEBUG=true
ENDOFFILE

cp .env.example .env

# ── Makefile ──────────────────────────────────────────────────────────────────
cat > Makefile << 'ENDOFFILE'
DC = docker compose -f infra/docker-compose.yml

.PHONY: up down build logs migrate rls seed test shell init

up:
	$(DC) up -d --build

down:
	$(DC) down

build:
	$(DC) build

logs:
	$(DC) logs -f backend

migrate:
	$(DC) exec backend alembic upgrade head

rls:
	$(DC) exec backend python -m app.db.init_rls

seed:
	$(DC) exec backend python -m app.db.seed

test:
	$(DC) exec backend pytest -v

shell:
	$(DC) exec backend bash

init: up migrate rls seed
	@echo "🚀  HMSK stack er klar. API: http://localhost:8000/docs"
ENDOFFILE

# ── infra/docker-compose.yml ──────────────────────────────────────────────────
cat > infra/docker-compose.yml << 'ENDOFFILE'
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-hmsk}
      POSTGRES_USER: ${POSTGRES_USER:-hmsk}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-changeme}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-hmsk}"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build:
      context: ../backend
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file:
      - ../.env
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ../backend:/app

volumes:
  pgdata:
ENDOFFILE

# ── backend/Dockerfile ────────────────────────────────────────────────────────
cat > backend/Dockerfile << 'ENDOFFILE'
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
ENDOFFILE

# ── backend/requirements.txt ──────────────────────────────────────────────────
cat > backend/requirements.txt << 'ENDOFFILE'
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy[asyncio]==2.0.30
asyncpg==0.29.0
psycopg2-binary==2.9.9
alembic==1.13.1
pydantic==2.7.1
pydantic-settings==2.2.1
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
httpx==0.27.0
pytest==8.2.0
pytest-asyncio==0.23.6
ENDOFFILE

# ── backend/alembic.ini ───────────────────────────────────────────────────────
cat > backend/alembic.ini << 'ENDOFFILE'
[alembic]
script_location = app/db/migrations
prepend_sys_path = .
sqlalchemy.url = postgresql+psycopg2://hmsk:changeme@localhost:5432/hmsk

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
ENDOFFILE

# ── backend/pytest.ini ────────────────────────────────────────────────────────
cat > backend/pytest.ini << 'ENDOFFILE'
[pytest]
asyncio_mode = auto
testpaths = tests
ENDOFFILE

# ── backend/app/settings.py ───────────────────────────────────────────────────
cat > backend/app/settings.py << 'ENDOFFILE'
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://hmsk:changeme@localhost:5432/hmsk"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://hmsk:changeme@localhost:5432/hmsk"

    JWT_SECRET: str = "CHANGE_ME_32_CHARS_MINIMUM_SECRET"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    APP_ENV: str = "development"
    APP_DEBUG: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
ENDOFFILE

# ── backend/app/main.py ───────────────────────────────────────────────────────
cat > backend/app/main.py << 'ENDOFFILE'
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.audit.service import AuditMiddleware
from app.core.auth.router import router as auth_router
from app.core.tenants.router import router as tenants_router
from app.core.rbac.router import router as rbac_router
from app.settings import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="HMSK Platform API",
        version="0.1.0",
        docs_url="/docs" if settings.APP_DEBUG else None,
        redoc_url="/redoc" if settings.APP_DEBUG else None,
    )

    app.add_middleware(AuditMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.APP_DEBUG else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(tenants_router)
    app.include_router(rbac_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
ENDOFFILE

# ── backend/app/dependencies.py ───────────────────────────────────────────────
cat > backend/app/dependencies.py << 'ENDOFFILE'
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
ENDOFFILE

# ── backend/app/db/base.py ────────────────────────────────────────────────────
cat > backend/app/db/base.py << 'ENDOFFILE'
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=text("now()"), nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, server_default=text("now()"), nullable=False,
    )


class SoftDeleteMixin:
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TenantScopedMixin:
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
ENDOFFILE

# ── backend/app/db/session.py ─────────────────────────────────────────────────
cat > backend/app/db/session.py << 'ENDOFFILE'
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.settings import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.APP_DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)


async def set_rls_context(
    session: AsyncSession,
    tenant_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
) -> None:
    t = str(tenant_id) if tenant_id else ""
    u = str(user_id) if user_id else ""
    await session.execute(text(f"SET LOCAL app.tenant_id = '{t}'"))
    await session.execute(text(f"SET LOCAL app.user_id   = '{u}'"))


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        async with session.begin():
            yield session
ENDOFFILE

# ── backend/app/db/init_rls.py ────────────────────────────────────────────────
cat > backend/app/db/init_rls.py << 'ENDOFFILE'
import os
import pathlib
import psycopg2

SQL_FILE = pathlib.Path(__file__).parent / "rls" / "init_rls.sql"


def apply_rls() -> None:
    url = os.environ["DATABASE_SYNC_URL"]
    sql = SQL_FILE.read_text()
    conn = psycopg2.connect(url)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.close()
    print("✅  RLS policies applied.")


if __name__ == "__main__":
    apply_rls()
ENDOFFILE

# ── backend/app/db/seed.py ────────────────────────────────────────────────────
cat > backend/app/db/seed.py << 'ENDOFFILE'
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
ENDOFFILE

# ── backend/app/db/rls/init_rls.sql ──────────────────────────────────────────
cat > backend/app/db/rls/init_rls.sql << 'ENDOFFILE'
-- RLS policies for all tenant-scoped tables.
-- App sets per-request: SET LOCAL app.tenant_id = '<uuid>'

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_role_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation ON users;
CREATE POLICY tenant_isolation ON users
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON roles;
CREATE POLICY tenant_isolation ON roles
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON user_role_assignments;
CREATE POLICY tenant_isolation ON user_role_assignments
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON refresh_tokens;
CREATE POLICY tenant_isolation ON refresh_tokens
    USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid);

DROP POLICY IF EXISTS tenant_isolation ON audit_log;
CREATE POLICY tenant_isolation ON audit_log
    USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    )
    WITH CHECK (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.tenant_id', true)::uuid
    );
ENDOFFILE

# ── backend/app/db/migrations/env.py ─────────────────────────────────────────
cat > backend/app/db/migrations/env.py << 'ENDOFFILE'
import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

from app.db.base import Base  # noqa
from app.core.tenants.models import Tenant  # noqa
from app.core.rbac.models import User, Role, UserRoleAssignment  # noqa
from app.core.auth.models import RefreshToken  # noqa
from app.core.audit.models import AuditLog  # noqa

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return os.environ.get("DATABASE_SYNC_URL", "postgresql+psycopg2://hmsk:changeme@localhost:5432/hmsk")


def run_migrations_offline() -> None:
    context.configure(url=get_url(), target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section, {})
    cfg["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
ENDOFFILE

# ── backend/app/db/migrations/script.py.mako ─────────────────────────────────
cat > backend/app/db/migrations/script.py.mako << 'ENDOFFILE'
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
ENDOFFILE

# ── backend/app/db/migrations/versions/0001_initial.py ───────────────────────
cat > backend/app/db/migrations/versions/0001_initial.py << 'ENDOFFILE'
"""Initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-01 00:00:00
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("plan", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("is_superadmin", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
    )
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("permissions", sa.Text, nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
    )

    op.create_table(
        "user_role_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "user_id", "role_id", name="uq_user_role_tenant"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_refresh_tokens_tenant_id", "refresh_tokens", ["tenant_id"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])

    op.create_table(
        "audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("detail", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_tenant_id", "audit_log", ["tenant_id"])
    op.create_index("ix_audit_log_tenant_created", "audit_log", ["tenant_id", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("refresh_tokens")
    op.drop_table("user_role_assignments")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("tenants")
ENDOFFILE

# ── backend/app/core/auth/security.py ────────────────────────────────────────
cat > backend/app/core/auth/security.py << 'ENDOFFILE'
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.settings import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "tenant_id": str(tenant_id), "type": "access", "exp": expires}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise JWTError("Wrong token type")
    return payload


def generate_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def hash_refresh_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()
ENDOFFILE

# ── backend/app/core/auth/models.py ──────────────────────────────────────────
cat > backend/app/core/auth/models.py << 'ENDOFFILE'
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
ENDOFFILE

# ── backend/app/core/auth/schemas.py ─────────────────────────────────────────
cat > backend/app/core/auth/schemas.py << 'ENDOFFILE'
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_slug: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
ENDOFFILE

# ── backend/app/core/auth/service.py ─────────────────────────────────────────
cat > backend/app/core/auth/service.py << 'ENDOFFILE'
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
ENDOFFILE

# ── backend/app/core/auth/router.py ──────────────────────────────────────────
cat > backend/app/core/auth/router.py << 'ENDOFFILE'
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
ENDOFFILE

# ── backend/app/core/tenants/models.py ───────────────────────────────────────
cat > backend/app/core/tenants/models.py << 'ENDOFFILE'
import uuid
from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, SoftDeleteMixin


class Tenant(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    plan: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
ENDOFFILE

# ── backend/app/core/tenants/schemas.py ──────────────────────────────────────
cat > backend/app/core/tenants/schemas.py << 'ENDOFFILE'
import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class TenantCreate(BaseModel):
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=100, pattern=r"^[a-z0-9-]+$")
    plan: str | None = None
    notes: str | None = None


class TenantUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    status: str | None = None
    plan: str | None = None
    notes: str | None = None


class TenantRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    slug: str
    status: str
    plan: str | None
    created_at: datetime
    updated_at: datetime
ENDOFFILE

# ── backend/app/core/tenants/service.py ──────────────────────────────────────
cat > backend/app/core/tenants/service.py << 'ENDOFFILE'
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
ENDOFFILE

# ── backend/app/core/tenants/router.py ───────────────────────────────────────
cat > backend/app/core/tenants/router.py << 'ENDOFFILE'
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
ENDOFFILE

# ── backend/app/core/rbac/models.py ──────────────────────────────────────────
cat > backend/app/core/rbac/models.py << 'ENDOFFILE'
import uuid
from sqlalchemy import String, Text, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin


class User(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    is_superadmin: Mapped[bool] = mapped_column(default=False, nullable=False)

    role_assignments: Mapped[list["UserRoleAssignment"]] = relationship(back_populates="user", lazy="selectin")

    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),)


class Role(Base, TimestampMixin, SoftDeleteMixin, TenantScopedMixin):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    permissions: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),)


class UserRoleAssignment(Base, TimestampMixin):
    __tablename__ = "user_role_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)

    user: Mapped["User"] = relationship(back_populates="role_assignments")
    role: Mapped["Role"] = relationship()

    __table_args__ = (UniqueConstraint("tenant_id", "user_id", "role_id", name="uq_user_role_tenant"),)
ENDOFFILE

# ── backend/app/core/rbac/schemas.py ─────────────────────────────────────────
cat > backend/app/core/rbac/schemas.py << 'ENDOFFILE'
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class RoleCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: str | None = None
    permissions: str | None = None


class RoleRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    permissions: str | None
    created_at: datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserUpdate(BaseModel):
    full_name: str | None = None
    status: str | None = None


class UserRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str | None
    status: str
    is_superadmin: bool
    created_at: datetime


class RoleAssignRequest(BaseModel):
    role_id: uuid.UUID


class UserRoleAssignmentRead(BaseModel):
    model_config = {"from_attributes": True}
    id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    tenant_id: uuid.UUID
    created_at: datetime
ENDOFFILE

# ── backend/app/core/rbac/service.py ─────────────────────────────────────────
cat > backend/app/core/rbac/service.py << 'ENDOFFILE'
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
ENDOFFILE

# ── backend/app/core/rbac/router.py ──────────────────────────────────────────
cat > backend/app/core/rbac/router.py << 'ENDOFFILE'
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
ENDOFFILE

# ── backend/app/core/audit/models.py ─────────────────────────────────────────
cat > backend/app/core/audit/models.py << 'ENDOFFILE'
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_audit_log_tenant_created", "tenant_id", "created_at"),)
ENDOFFILE

# ── backend/app/core/audit/service.py ────────────────────────────────────────
cat > backend/app/core/audit/service.py << 'ENDOFFILE'
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.audit.models import AuditLog


class AuditContext:
    def __init__(self, request: Request):
        forwarded = request.headers.get("x-forwarded-for", "")
        self.ip_address: str | None = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        request.state.audit_ctx = AuditContext(request)
        return await call_next(request)


async def audit(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    user_id: uuid.UUID | None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        detail=detail,
        ip_address=ip_address,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.flush()
    return entry
ENDOFFILE

# ── tests/ ────────────────────────────────────────────────────────────────────
cat > tests/conftest.py << 'ENDOFFILE'
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
ENDOFFILE

cat > tests/test_auth.py << 'ENDOFFILE'
from app.core.auth.security import hash_password, verify_password, create_access_token, decode_access_token, generate_refresh_token, hash_refresh_token
import uuid


def test_password_hash_roundtrip():
    plain = "MyS3cure!Pass"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    user_id, tenant_id = uuid.uuid4(), uuid.uuid4()
    token = create_access_token(user_id, tenant_id)
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)


def test_refresh_token_hash():
    raw, hashed = generate_refresh_token()
    assert hashed == hash_refresh_token(raw)
ENDOFFILE

cat > tests/test_health.py << 'ENDOFFILE'
import pytest


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
ENDOFFILE

echo "✅  Alle filer skrevet"

# =============================================================================
# GIT + GITHUB
# =============================================================================

# Init git hvis ikke allerede gjort
if [ ! -d ".git" ]; then
  git init
  git branch -M main
fi

git add -A
git commit -m "feat: Sprint 1 – backend scaffold, auth, RBAC, RLS, Alembic"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📡  Klar til å pushe til GitHub."
echo ""
echo "Velg autentiseringsmetode:"
echo ""
echo "  A) GitHub CLI (anbefalt, enklest):"
echo "     gh auth login"
echo "     git remote add origin https://github.com/${GITHUB_USER}/${REPO_NAME}.git"
echo "     git push -u origin main"
echo ""
echo "  B) Personal Access Token (PAT):"
echo "     git remote add origin https://<TOKEN>@github.com/${GITHUB_USER}/${REPO_NAME}.git"
echo "     git push -u origin main"
echo ""
echo "  C) SSH (hvis du har SSH-nøkkel på GitHub):"
echo "     git remote add origin git@github.com:${GITHUB_USER}/${REPO_NAME}.git"
echo "     git push -u origin main"
echo ""
echo "  (Opprett repo på GitHub først: https://github.com/new)"
echo "   Navn: ${REPO_NAME} | Owner: ${GITHUB_USER} | Tom repo, ingen README)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Etter push, start stacken med:"
echo "  make init"
echo ""
echo "API docs: http://localhost:8000/docs"
