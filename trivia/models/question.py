from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from .. import db

class TriviaQuestion(db.Model):
    __tablename__ = 'trivia_questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(db.Text, nullable=False)
    answer: Mapped[str] = mapped_column(db.Text, nullable=False)
    category_id: Mapped[int] = mapped_column(db.ForeignKey('categories.id'), nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(db.String(10), nullable=False, index=True)  # 'easy', 'medium', or 'hard'
    air_date: Mapped[Optional[datetime]] = mapped_column(db.Date, nullable=True)
    original_value: Mapped[Optional[int]] = mapped_column(db.SmallInteger, nullable=True)
    original_round: Mapped[Optional[int]] = mapped_column(db.SmallInteger, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)

    # Relationships
    category: Mapped["Category"] = relationship("Category", back_populates="trivia_questions")
    round_associations: Mapped[List["RoundQuestion"]] = relationship("RoundQuestion", back_populates="preset_question")

class UserGeneratedQuestion(db.Model):
    __tablename__ = 'user_generated_questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(db.Text, nullable=False)
    answer: Mapped[str] = mapped_column(db.Text, nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('categories.id'), index=True)
    difficulty: Mapped[str] = mapped_column(db.String(10), nullable=False)  # 'easy', 'medium', or 'hard'
    created_by: Mapped[Optional[int]] = mapped_column(db.ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), server_default=db.func.now())
    status: Mapped[str] = mapped_column(db.String(50), default='active', server_default='active')  # active, flagged, deleted, etc.
    notes: Mapped[Optional[str]] = mapped_column(db.Text, nullable=True)

    # Relationships
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="user_questions")
    creator: Mapped[Optional["User"]] = relationship("User", back_populates="user_questions")
    round_associations: Mapped[List["RoundQuestion"]] = relationship("RoundQuestion", back_populates="user_question") 