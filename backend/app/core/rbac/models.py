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
