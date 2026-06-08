from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    category: Mapped[str] = mapped_column(String(100), index=True)
    difficulty: Mapped[str] = mapped_column(String(50), index=True)
    question_type: Mapped[str] = mapped_column(String(50), default="short_answer")
    question: Mapped[str] = mapped_column(Text)
    standard_answer: Mapped[str] = mapped_column(Text)
    rubric: Mapped[list[str]] = mapped_column(JSON, default=list)
    options: Mapped[list[str]] = mapped_column(JSON, default=list)
    correct_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
