import bcrypt
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import func
from typing import List, Optional
from ..database import db

class User(db.Model):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(db.String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(db.String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), server_default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)

    # Relationships
    sessions: Mapped[List["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    events_created: Mapped[List["Event"]] = relationship("Event", back_populates="creator", foreign_keys="Event.user_id")
    user_questions: Mapped[List["UserGeneratedQuestion"]] = relationship("UserGeneratedQuestion", back_populates="creator")

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))

class UserSession(db.Model):
    __tablename__ = 'user_sessions'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('users.id', ondelete='CASCADE'), index=True)
    session_token: Mapped[str] = mapped_column(db.String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions") 