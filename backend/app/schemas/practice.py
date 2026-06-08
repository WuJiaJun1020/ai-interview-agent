from pydantic import BaseModel, Field

from app.schemas.question import QuestionRead


class PracticeAnswerCreate(BaseModel):
    question_id: int
    answer: str = Field(..., min_length=1)


class PracticeAnswerResult(BaseModel):
    question: QuestionRead
    score: int
    feedback: str
    matched_rubric: list[str]
    missing_rubric: list[str]
    standard_answer: str
