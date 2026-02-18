from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.audit.service import AuditMiddleware
from app.core.auth.router import router as auth_router
from app.core.tenants.router import router as tenants_router
from app.core.rbac.router import router as rbac_router
from app.core.projects.router import router as projects_router
from app.core.inbox.router import router as inbox_router
from app.core.tasks.router import router as tasks_router
from app.core.incidents.router import router as incidents_router
from app.core.nonconformance.router import router as nc_router
from app.core.documents.router import router as documents_router
from app.core.checklists.router import router as checklists_router
from app.core.drawings.router import router as drawings_router
from app.core.timesheets.router import router as timesheets_router
from app.settings import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    app = FastAPI(
        title="HMSK Platform API",
        version="0.7.0",
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
    app.include_router(projects_router)
    app.include_router(inbox_router)
    app.include_router(tasks_router)
    app.include_router(incidents_router)
    app.include_router(nc_router)
    app.include_router(documents_router)
    app.include_router(checklists_router)
    app.include_router(drawings_router)
    app.include_router(timesheets_router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
