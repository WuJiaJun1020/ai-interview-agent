from pydantic import BaseModel, Field


class QuestionCreate(BaseModel):
    category: str = Field(..., min_length=1, max_length=100)
    difficulty: str = Field(..., min_length=1, max_length=50)
    question: str = Field(..., min_length=1)
    standard_answer: str = Field(..., min_length=1)
    rubric: list[str] = Field(default_factory=list)


class QuestionUpdate(QuestionCreate):
    pass


class QuestionRead(QuestionCreate):
    id: int

    model_config = {"from_attributes": True}
