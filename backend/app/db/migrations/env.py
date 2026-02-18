import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from app.db.base import Base  # noqa
from app.core.tenants.models import Tenant  # noqa
from app.core.rbac.models import User, Role, UserRoleAssignment  # noqa
from app.core.auth.models import RefreshToken  # noqa
from app.core.audit.models import AuditLog  # noqa
from app.core.projects.models import Project, ProjectSequence  # noqa
from app.core.inbox.models import MessageThread, IncomingMessage, IncomingAttachment  # noqa
from app.core.tasks.models import Task  # noqa
from app.core.files.models import File, FileLink  # noqa
from app.core.incidents.models import Incident, IncidentMessage  # noqa
from app.core.nonconformance.models import Nonconformance, CapaAction  # noqa

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
