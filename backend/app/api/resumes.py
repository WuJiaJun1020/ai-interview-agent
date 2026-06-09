from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.resume import Resume, ResumeAnalysis
from app.schemas.resume import ResumeAnalyzeRead, ResumeHistoryItem, ResumeUploadRead
from app.services.resume_analysis import analyze_resume_text
from app.services.resume_text import extract_resume_text
from app.services.job_vector_store import recommendation_bundle_to_json, recommend_jobs_for_resume

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.post("/upload", response_model=ResumeUploadRead, status_code=201)
async def upload_resume_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    filename = file.filename or "resume"
    content_type = file.content_type or ""

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Uploaded resume is empty")

    try:
        content = extract_resume_text(file_bytes, filename, content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to extract resume text: {exc}") from exc

    if len(content.strip()) < 20:
        raise HTTPException(status_code=400, detail="Resume text is too short or cannot be extracted")

    resume = Resume(filename=filename, content_type=content_type, content=content)
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return _upload_payload(resume)


@router.post("/{resume_id}/analyze", response_model=ResumeAnalyzeRead, status_code=201)
def analyze_uploaded_resume(resume_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    recommendation_bundle = recommendation_bundle_to_json(recommend_jobs_for_resume(db, resume.content, limit=8))
    result = analyze_resume_text(resume.content, recommendation_bundle)
    result.job_recommendations = recommendation_bundle
    analysis = ResumeAnalysis(resume_id=resume.id, **result.__dict__)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return _analysis_payload(resume, analysis)


@router.post("/analyze", response_model=ResumeAnalyzeRead, status_code=201)
async def analyze_resume_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    upload = await upload_resume_document(file=file, db=db)
    return analyze_uploaded_resume(int(upload["resume_id"]), db)


@router.get("", response_model=list[ResumeHistoryItem])
def list_resumes(db: Session = Depends(get_db)) -> list[dict[str, object]]:
    resumes = db.scalars(select(Resume).order_by(desc(Resume.created_at), desc(Resume.id))).all()
    return [_history_payload(resume, _latest_analysis(db, resume.id)) for resume in resumes]


@router.get("/{resume_id}", response_model=ResumeAnalyzeRead)
def get_resume_result(resume_id: int, db: Session = Depends(get_db)) -> dict[str, object]:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    analysis = _latest_analysis(db, resume.id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Resume analysis not found")
    return _analysis_payload(resume, analysis)


@router.delete("/{resume_id}", status_code=204)
def delete_resume_result(resume_id: int, db: Session = Depends(get_db)) -> None:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")

    db.execute(delete(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume.id))
    db.delete(resume)
    db.commit()


def _latest_analysis(db: Session, resume_id: int) -> ResumeAnalysis | None:
    return db.scalar(
        select(ResumeAnalysis)
        .where(ResumeAnalysis.resume_id == resume_id)
        .order_by(desc(ResumeAnalysis.id))
    )


def _upload_payload(resume: Resume) -> dict[str, object]:
    return {
        "resume_id": resume.id,
        "filename": resume.filename,
        "created_at": resume.created_at,
        "extracted_chars": len(resume.content),
        "content_preview": resume.content[:240],
    }


def _analysis_payload(resume: Resume, analysis: ResumeAnalysis) -> dict[str, object]:
    return {
        "resume_id": resume.id,
        "filename": resume.filename,
        "created_at": resume.created_at,
        "extracted_chars": len(resume.content),
        "analysis": analysis,
    }


def _history_payload(resume: Resume, analysis: ResumeAnalysis | None) -> dict[str, object]:
    return {
        "resume_id": resume.id,
        "filename": resume.filename,
        "created_at": resume.created_at,
        "extracted_chars": len(resume.content),
        "latest_analysis": analysis,
    }
