from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import relationship, Mapped, selectinload
from sqlalchemy.ext.declarative import declarative_base
import enum
from datetime import datetime
from typing import Optional, List

Base = declarative_base()

class QueryStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    email: Mapped[str] = Column(String, unique=True, index=True)
    hashed_password: Mapped[str] = Column(String)
    is_active: Mapped[bool] = Column(Boolean, default=True)
    
    # Relationships with lazy="selectin" for async loading
    settings: Mapped["UserSettings"] = relationship(
        "UserSettings", 
        back_populates="user", 
        uselist=False,
        lazy="selectin"
    )
    queries: Mapped[List["Query"]] = relationship(
        "Query", 
        back_populates="user",
        lazy="selectin"
    )

class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"))
    export_location: Mapped[Optional[str]] = Column(String)
    export_type: Mapped[Optional[str]] = Column(String)
    max_parallel_queries: Mapped[Optional[int]] = Column(Integer)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="settings")

class Query(Base):
    __tablename__ = "queries"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), index=True)
    db_username: Mapped[str] = Column(String)
    db_password: Mapped[str] = Column(String)
    db_tns: Mapped[str] = Column(String)
    query_text: Mapped[str] = Column(String)
    status: Mapped[str] = Column(String, nullable=False, default=QueryStatus.PENDING.value)
    export_location: Mapped[Optional[str]] = Column(String)
    export_type: Mapped[Optional[str]] = Column(String)
    created_at: Mapped[datetime] = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at: Mapped[Optional[datetime]] = Column(DateTime)
    completed_at: Mapped[Optional[datetime]] = Column(DateTime)
    error_message: Mapped[Optional[str]] = Column(String)
    result_metadata: Mapped[Optional[dict]] = Column(JSON)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="queries") 