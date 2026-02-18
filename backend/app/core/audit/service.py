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
