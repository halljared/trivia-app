from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from .. import db

class Event(db.Model):
    __tablename__ = 'events'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(255), nullable=False)
    user_id: Mapped[int] = mapped_column(db.ForeignKey('users.id'))
    event_date: Mapped[Optional[datetime]] = mapped_column(db.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), server_default=db.func.now())
    status: Mapped[str] = mapped_column(db.String(50), default='draft', server_default='draft')
    description: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(db.Boolean, default=False, server_default='false')

    # Relationships
    creator: Mapped["User"] = relationship("User", back_populates="events_created", foreign_keys=[user_id])
    rounds: Mapped[List["Round"]] = relationship("Round", back_populates="event", cascade="all, delete-orphan", order_by="Round.round_number") 