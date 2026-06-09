from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.job import JobPost
from app.schemas.job import JobImportRead, JobPostRead, JobVectorStatusRead
from app.services.job_importer import import_jobs_jsonl
from app.services.job_vector_store import get_job_vector_status, rebuild_job_vector_index

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("/import-jsonl", response_model=JobImportRead)
async def import_jobs_jsonl_file(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict[str, object]:
    if not file.filename or not file.filename.lower().endswith(".jsonl"):
        raise HTTPException(status_code=400, detail="Only JSONL job files are supported")

    try:
        result = import_jobs_jsonl(db, await file.read(), file.filename)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Job import failed: {exc}") from exc

    return {
        "filename": file.filename,
        "imported_count": result.imported_count,
        "created_count": result.created_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
        "failed_count": result.failed_count,
        "errors": result.errors,
        "jobs": result.jobs,
    }


@router.get("", response_model=list[JobPostRead])
def list_jobs(
    company: str | None = Query(default=None),
    skill: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[JobPost]:
    statement = select(JobPost).order_by(desc(JobPost.fetched_at), desc(JobPost.id)).limit(limit)
    if company:
        statement = statement.where(JobPost.company == company)
    jobs = list(db.scalars(statement).all())
    if skill:
        jobs = [job for job in jobs if skill in (job.skills or [])]
    if q:
        keyword = q.strip().lower()
        jobs = [
            job
            for job in jobs
            if keyword in _job_search_text(job)
        ]
    return jobs


def _job_search_text(job: JobPost) -> str:
    return " ".join(
        [
            job.company or "",
            job.title or "",
            job.city or "",
            job.job_family or "",
            job.seniority or "",
            job.description or "",
            job.requirements or "",
            " ".join(job.skills or []),
        ]
    ).lower()


@router.get("/vector-index/status", response_model=JobVectorStatusRead)
def job_vector_index_status() -> dict[str, object]:
    return get_job_vector_status().__dict__


@router.post("/vector-index/rebuild", response_model=JobVectorStatusRead)
def rebuild_jobs_vector_index(db: Session = Depends(get_db)) -> dict[str, object]:
    return rebuild_job_vector_index(db).__dict__
