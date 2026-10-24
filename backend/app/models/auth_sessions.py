from sqlalchemy import String, ForeignKey, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.session import Base
from backend.app.models.entities import now


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[str] = mapped_column(String(50), default=now)
    expires_at: Mapped[str] = mapped_column(String(50))
    revoked_at: Mapped[str | None] = mapped_column(String(50), nullable=True)


class LoginAttemptBucket(Base):
    __tablename__ = "login_attempt_buckets"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    failed_at: Mapped[list] = mapped_column(JSON)
    expires_at: Mapped[float] = mapped_column(Float, index=True)
