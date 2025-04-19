from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List
from .. import db

class Category(db.Model):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(db.String(256), unique=True, nullable=False)

    # Relationships
    trivia_questions: Mapped[List["TriviaQuestion"]] = relationship("TriviaQuestion", back_populates="category")
    rounds: Mapped[List["Round"]] = relationship("Round", back_populates="category")
    user_questions: Mapped[List["UserGeneratedQuestion"]] = relationship("UserGeneratedQuestion", back_populates="category") 