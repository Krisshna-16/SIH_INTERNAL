import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum
from app.db.session import Base


class UserRole(str, enum.Enum):
    INVESTIGATOR = "INVESTIGATOR"


class User(Base):
    """
    User model for authentication and audit trail identity.
    Single role (INVESTIGATOR) for MVP, extensible for future RBAC.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(128), unique=True, nullable=False, index=True)
    hashed_password = Column(String(256), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.INVESTIGATOR, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"
