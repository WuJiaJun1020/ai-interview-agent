from datetime import datetime

from pydantic import BaseModel


class JobPostRead(BaseModel):
    id: int
    source_name: str
    source_url: str
    company: str
    title: str
    city: str | None
    job_family: str | None
    seniority: str | None
    description: str
    requirements: str
    skills: list[str]
    fetched_at: datetime

    model_config = {"from_attributes": True}


class JobImportRead(BaseModel):
    filename: str
    imported_count: int
    created_count: int
    updated_count: int
    skipped_count: int
    failed_count: int
    errors: list[str]
    jobs: list[JobPostRead]


class JobVectorStatusRead(BaseModel):
    exists: bool
    path: str
    job_count: int
    chunk_count: int
    built_at: str | None = None
    version: int | None = None
    backend: str = "local_hash"
    collection_name: str | None = None
    chroma_available: bool = False
    fallback_path: str | None = None
    error: str | None = None
