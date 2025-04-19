from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import UniqueConstraint, CheckConstraint
from typing import List, Optional
from ..database import db

class Round(db.Model):
    __tablename__ = 'rounds'
    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(db.ForeignKey('events.id', ondelete='CASCADE'), index=True)
    category_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('categories.id'), nullable=True)
    round_number: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[Optional[str]] = mapped_column(db.String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), server_default=db.func.now())
    is_deleted: Mapped[bool] = mapped_column(db.Boolean, default=False, server_default='false')

    __table_args__ = (UniqueConstraint('event_id', 'round_number', name='uq_rounds_event_round'),)

    # Relationships
    event: Mapped["Event"] = relationship("Event", back_populates="rounds")
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="rounds")
    questions: Mapped[List["RoundQuestion"]] = relationship("RoundQuestion", back_populates="round", cascade="all, delete-orphan", order_by="RoundQuestion.question_number")
    normalized_questions: Mapped[List["NormalizedQuestion"]] = relationship(
        "NormalizedQuestion",
        primaryjoin="Round.id == NormalizedQuestion.round_id",
        order_by="NormalizedQuestion.question_number",
        viewonly=True
    )

class RoundQuestion(db.Model):
    __tablename__ = 'round_questions'
    id: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[int] = mapped_column(db.ForeignKey('rounds.id', ondelete='CASCADE'))
    question_number: Mapped[int] = mapped_column(nullable=False)
    preset_question_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('trivia_questions.id'), index=True, nullable=True)
    user_question_id: Mapped[Optional[int]] = mapped_column(db.ForeignKey('user_generated_questions.id'), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(db.DateTime(timezone=True), server_default=db.func.now())

    __table_args__ = (
        UniqueConstraint('round_id', 'question_number', name='uq_round_questions_round_number'),
        CheckConstraint(
            '(preset_question_id IS NULL AND user_question_id IS NOT NULL) OR (preset_question_id IS NOT NULL AND user_question_id IS NULL)',
            name='ck_round_questions_question_type'
        )
    )

    # Relationships
    round: Mapped["Round"] = relationship("Round", back_populates="questions")
    preset_question: Mapped[Optional["TriviaQuestion"]] = relationship("TriviaQuestion", back_populates="round_associations")
    user_question: Mapped[Optional["UserGeneratedQuestion"]] = relationship("UserGeneratedQuestion", back_populates="round_associations")

    @property
    def question_object(self):
        return self.preset_question or self.user_question

class NormalizedQuestion(db.Model):
    __tablename__ = 'normalized_questions_view'
    
    round_question_id: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[int] = mapped_column(db.ForeignKey('rounds.id'))
    question_number: Mapped[int] = mapped_column()
    question_id: Mapped[int] = mapped_column()
    question_type: Mapped[str] = mapped_column(db.String(10))
    question: Mapped[str] = mapped_column(db.Text)
    answer: Mapped[str] = mapped_column(db.Text)
    difficulty: Mapped[str] = mapped_column(db.String(10))
    category_id: Mapped[Optional[int]] = mapped_column()
    category_name: Mapped[str] = mapped_column(db.String(256))

    __table_args__ = (
        {'info': {'is_view': True}}  # Mark this as a view
    )

    # Make it effectively immutable
    __mapper_args__ = {
        'confirm_deleted_rows': False
    } 