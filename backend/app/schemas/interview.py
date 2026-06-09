from pydantic import BaseModel, Field


class HrInterviewStartCreate(BaseModel):
    resume_id: int
    job_id: int
    total_questions: int = Field(default=3, ge=1, le=8)


class HrInterviewQuestionRead(BaseModel):
    question: str
    focus: list[str] = Field(default_factory=list)


class HrInterviewContextRead(BaseModel):
    resume_id: int
    resume_filename: str
    job_id: int
    job_title: str
    company: str
    city: str | None = None
    skills: list[str] = Field(default_factory=list)


class HrInterviewStartResult(BaseModel):
    session_id: int
    context: HrInterviewContextRead
    current_question: HrInterviewQuestionRead
    answered_count: int
    total_questions: int
    is_finished: bool
    source: str


class HrInterviewAnswerCreate(BaseModel):
    answer: str = Field(..., min_length=1)


class HrInterviewAnswerResult(BaseModel):
    session_id: int
    score: int
    source: str
    feedback: str
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    next_question: HrInterviewQuestionRead | None
    answered_count: int
    total_questions: int
    is_finished: bool


class HrInterviewReportItem(BaseModel):
    question: str
    answer: str
    score: int
    source: str
    feedback: str
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]


class HrInterviewReport(BaseModel):
    session_id: int
    context: HrInterviewContextRead
    answered_count: int
    total_questions: int
    average_score: float
    is_finished: bool
    recommendation: str
    answers: list[HrInterviewReportItem]
