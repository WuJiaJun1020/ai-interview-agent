from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class HrInterviewSession(Base):
    __tablename__ = "hr_interview_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"), index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_posts.id"), index=True)
    total_questions: Mapped[int] = mapped_column(Integer, default=3)
    current_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_focus: Mapped[list[str]] = mapped_column(JSON, default=list)
    answered_count: Mapped[int] = mapped_column(Integer, default=0)
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    is_finished: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(50), default="mock")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class HrInterviewAnswer(Base):
    __tablename__ = "hr_interview_answers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("hr_interview_sessions.id"), index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    score: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(50), default="mock")
    feedback: Mapped[str] = mapped_column(Text)
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list[str]] = mapped_column(JSON, default=list)
    suggestions: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
