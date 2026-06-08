from pydantic import BaseModel, Field

from app.schemas.question import QuestionRead


class PracticeAnswerCreate(BaseModel):
    question_id: int
    answer: str = Field(..., min_length=1)


class PracticeAnswerResult(BaseModel):
    question: QuestionRead
    score: int
    source: str
    feedback: str
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    matched_rubric: list[str]
    missing_rubric: list[str]
    standard_answer: str
