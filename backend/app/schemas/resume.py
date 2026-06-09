from datetime import datetime

from pydantic import BaseModel, Field


class ResumeAnalysisRead(BaseModel):
    id: int
    resume_id: int
    source: str
    target_roles: list[str]
    skills: list[str]
    strengths: list[str]
    weaknesses: list[str]
    suggested_categories: list[str]
    suggested_difficulty: str
    interview_focus: list[str]
    job_recommendations: dict = Field(default_factory=dict)
    raw_feedback: str

    model_config = {"from_attributes": True}


class ResumeAnalyzeRead(BaseModel):
    resume_id: int
    filename: str
    created_at: datetime
    extracted_chars: int
    analysis: ResumeAnalysisRead

    model_config = {"from_attributes": True}


class ResumeUploadRead(BaseModel):
    resume_id: int
    filename: str
    created_at: datetime
    extracted_chars: int
    content_preview: str


class ResumeHistoryItem(BaseModel):
    resume_id: int
    filename: str
    created_at: datetime
    extracted_chars: int
    latest_analysis: ResumeAnalysisRead | None = None
