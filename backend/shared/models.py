from sqlalchemy import Boolean, Column, Integer, String, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.orm import relationship, Mapped, selectinload
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum
from datetime import datetime
from typing import Optional, List

Base = declarative_base()

class QueryStatus(str, enum.Enum):
    pending = "pending"
    queued = "queued"
    running = "running"
    transferring = "transferring"  # New status for file transfer stage
    completed = "completed"
    failed = "failed"

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
    
    # SSH Settings
    ssh_hostname: Mapped[Optional[str]] = Column(String)
    ssh_port: Mapped[Optional[int]] = Column(Integer, default=22)
    ssh_username: Mapped[Optional[str]] = Column(String)
    ssh_password: Mapped[Optional[str]] = Column(String)
    ssh_key: Mapped[Optional[str]] = Column(String)  # Store the SSH key content or path
    ssh_key_passphrase: Mapped[Optional[str]] = Column(String)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="settings")

class Query(Base):
    __tablename__ = "queries"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = Column(Integer, ForeignKey("users.id"), index=True)
    query_text: Mapped[str] = Column(String, nullable=False)
    db_username: Mapped[str] = Column(String, nullable=False)
    db_password: Mapped[str] = Column(String, nullable=False)
    db_tns: Mapped[str] = Column(String, nullable=False)
    status: Mapped[str] = Column(String, default=QueryStatus.pending.value)
    error_message: Mapped[Optional[str]] = Column(String)
    result_metadata: Mapped[Optional[dict]] = Column(JSON)
    export_location: Mapped[Optional[str]] = Column(String)
    export_type: Mapped[Optional[str]] = Column(String)
    export_filename: Mapped[Optional[str]] = Column(String)  # Optional custom filename for exported file
    ssh_hostname: Mapped[Optional[str]] = Column(String)  # Optional SSH hostname for remote execution
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))  # When query execution starts
    updated_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at: Mapped[Optional[datetime]] = Column(DateTime(timezone=True))
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="queries") 