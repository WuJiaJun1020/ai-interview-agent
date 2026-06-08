from pydantic import BaseModel, Field

from app.schemas.question import QuestionRead


class InterviewStartCreate(BaseModel):
    category: str | None = None
    difficulty: str | None = None
    total_questions: int = Field(default=3, ge=1, le=10)


class InterviewStartResult(BaseModel):
    session_id: int
    current_question: QuestionRead
    answered_count: int
    total_questions: int
    is_finished: bool


class InterviewAnswerCreate(BaseModel):
    answer: str = Field(..., min_length=1)


class InterviewAnswerResult(BaseModel):
    session_id: int
    score: int
    feedback: str
    standard_answer: str
    next_question: QuestionRead | None
    answered_count: int
    total_questions: int
    is_finished: bool


class InterviewReport(BaseModel):
    session_id: int
    answered_count: int
    total_questions: int
    average_score: float
    is_finished: bool
    recommendation: str
