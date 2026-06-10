import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.interview import HrInterviewAnswer, HrInterviewSession
from app.models.job import JobPost
from app.models.resume import Resume
from app.core.config import settings
from app.schemas.interview import (
    HrInterviewAnswerCreate,
    HrInterviewAnswerResult,
    HrInterviewContextRead,
    HrInterviewQuestionRead,
    HrInterviewReport,
    HrInterviewReportItem,
    HrInterviewSessionSummary,
    HrInterviewStartCreate,
    HrInterviewStartResult,
)
from app.services.hr_interview import (
    HrAnswerReview,
    HrQuestion,
    assess_hr_answer_attitude,
    build_hr_recommendation,
    generate_hr_question,
    heuristic_hr_attitude_reason,
    review_hr_answer,
    stream_hr_answer_review,
    stream_hr_question,
)

router = APIRouter(prefix="/api/interview", tags=["interview"])


@router.post("/hr-sessions", response_model=HrInterviewStartResult, status_code=201)
def start_hr_interview(payload: HrInterviewStartCreate, db: Session = Depends(get_db)) -> HrInterviewStartResult:
    resume = _get_resume_or_404(db, payload.resume_id)
    job = _get_job_or_404(db, payload.job_id)
    first_question = generate_hr_question(
        resume=resume,
        job=job,
        previous_turns=[],
        question_index=1,
        total_questions=payload.total_questions,
    )

    session = HrInterviewSession(
        resume_id=resume.id,
        job_id=job.id,
        total_questions=payload.total_questions,
        current_question=first_question.question,
        current_focus=first_question.focus,
        source=first_question.source,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return HrInterviewStartResult(
        session_id=session.id,
        context=_hr_context(resume, job),
        current_question=HrInterviewQuestionRead(question=first_question.question, focus=first_question.focus),
        answered_count=session.answered_count,
        total_questions=session.total_questions,
        is_finished=session.is_finished,
        source=first_question.source,
    )


@router.post("/hr-sessions/stream")
def start_hr_interview_stream(payload: HrInterviewStartCreate, db: Session = Depends(get_db)) -> StreamingResponse:
    resume = _get_resume_or_404(db, payload.resume_id)
    job = _get_job_or_404(db, payload.job_id)
    bind = db.get_bind()
    resume_id = resume.id
    job_id = job.id
    total_questions = payload.total_questions

    def events() -> Iterator[str]:
        with Session(bind=bind) as stream_db:
            try:
                stream_resume = _get_resume_or_404(stream_db, resume_id)
                stream_job = _get_job_or_404(stream_db, job_id)
                yield _sse_event("progress", {"message": "正在结合简历和岗位 JD 生成第一道面试题。"})
                first_question: HrQuestion | None = None
                for item in stream_hr_question(
                    resume=stream_resume,
                    job=stream_job,
                    previous_turns=[],
                    question_index=1,
                    total_questions=total_questions,
                ):
                    if item["type"] == "delta":
                        yield _sse_event("delta", {"target": "question", "text": item["text"]})
                    elif item["type"] == "progress":
                        yield _sse_event("progress", {"message": item["message"]})
                    elif item["type"] == "result":
                        first_question = item["question"]

                if first_question is None:
                    raise RuntimeError("HR interview question generation failed")

                session = HrInterviewSession(
                    resume_id=stream_resume.id,
                    job_id=stream_job.id,
                    total_questions=total_questions,
                    current_question=first_question.question,
                    current_focus=first_question.focus,
                    source=first_question.source,
                )
                stream_db.add(session)
                stream_db.commit()
                stream_db.refresh(session)
                yield _sse_event(
                    "result",
                    HrInterviewStartResult(
                        session_id=session.id,
                        context=_hr_context(stream_resume, stream_job),
                        current_question=HrInterviewQuestionRead(
                            question=first_question.question,
                            focus=first_question.focus,
                        ),
                        answered_count=session.answered_count,
                        total_questions=session.total_questions,
                        is_finished=session.is_finished,
                        source=first_question.source,
                    ).model_dump(),
                )
            except Exception as exc:
                stream_db.rollback()
                yield _sse_event("error", {"message": f"岗位 HR 面试题生成失败：{exc}"})

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/hr-sessions/{session_id}/answer", response_model=HrInterviewAnswerResult)
def submit_hr_interview_answer(
    session_id: int,
    payload: HrInterviewAnswerCreate,
    db: Session = Depends(get_db),
) -> HrInterviewAnswerResult:
    session = db.get(HrInterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="HR interview session not found")
    if session.is_finished:
        raise HTTPException(status_code=400, detail="HR interview session is finished")
    if not session.current_question:
        raise HTTPException(status_code=400, detail="Current HR interview question is missing")

    resume = _get_resume_or_404(db, session.resume_id)
    job = _get_job_or_404(db, session.job_id)
    previous_turns = _hr_previous_turns(db, session.id)
    current_question = session.current_question
    review = review_hr_answer(
        resume=resume,
        job=job,
        question=current_question,
        answer=payload.answer,
        previous_turns=previous_turns,
    )

    db.add(
        HrInterviewAnswer(
            session_id=session.id,
            question=current_question,
            answer=payload.answer,
            score=review.score,
            source=review.source,
            focus=session.current_focus,
            feedback=review.feedback,
            strengths=review.strengths,
            weaknesses=review.weaknesses,
            suggestions=review.suggestions,
        )
    )

    session.answered_count += 1
    session.total_score += review.score

    next_question = None
    attitude = assess_hr_answer_attitude(
        resume=resume,
        job=job,
        question=current_question,
        answer=payload.answer,
        previous_turns=previous_turns,
    )
    termination_reason = attitude.reason if attitude.should_terminate else None
    if termination_reason or session.answered_count >= session.total_questions:
        session.is_finished = True
        session.current_question = None
        session.current_focus = []
        session.termination_reason = termination_reason
    else:
        next_question = generate_hr_question(
            resume=resume,
            job=job,
            previous_turns=[
                *previous_turns,
                {"question": current_question, "answer": payload.answer, "score": review.score},
            ],
            question_index=session.answered_count + 1,
            total_questions=session.total_questions,
        )
        session.current_question = next_question.question
        session.current_focus = next_question.focus
        session.source = next_question.source

    db.commit()
    average_score = _average_score(session.total_score, session.answered_count)

    return HrInterviewAnswerResult(
        session_id=session.id,
        score=review.score,
        source=review.source,
        feedback=review.feedback,
        strengths=review.strengths,
        weaknesses=review.weaknesses,
        suggestions=review.suggestions,
        next_question=HrInterviewQuestionRead(question=next_question.question, focus=next_question.focus)
        if next_question
        else None,
        answered_count=session.answered_count,
        total_questions=session.total_questions,
        is_finished=session.is_finished,
        termination_reason=termination_reason,
        pass_score=settings.interview_pass_score,
        passed=(_passed(average_score) and not termination_reason) if session.is_finished else None,
    )


@router.post("/hr-sessions/{session_id}/answer/stream")
def submit_hr_interview_answer_stream(
    session_id: int,
    payload: HrInterviewAnswerCreate,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    session = db.get(HrInterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="HR interview session not found")
    if session.is_finished:
        raise HTTPException(status_code=400, detail="HR interview session is finished")
    if not session.current_question:
        raise HTTPException(status_code=400, detail="Current HR interview question is missing")

    resume = _get_resume_or_404(db, session.resume_id)
    job = _get_job_or_404(db, session.job_id)
    previous_turns = _hr_previous_turns(db, session.id)
    current_question = session.current_question
    bind = db.get_bind()
    resume_id = resume.id
    job_id = job.id

    def events() -> Iterator[str]:
        with Session(bind=bind) as stream_db:
            try:
                stream_session = stream_db.get(HrInterviewSession, session_id)
                if stream_session is None:
                    raise RuntimeError("HR interview session not found")
                if stream_session.is_finished:
                    raise RuntimeError("HR interview session is finished")
                stream_resume = _get_resume_or_404(stream_db, resume_id)
                stream_job = _get_job_or_404(stream_db, job_id)

                yield _sse_event("progress", {"message": "面试官正在阅读你的回答并给出反馈。"})
                review: HrAnswerReview | None = None
                for item in stream_hr_answer_review(
                    resume=stream_resume,
                    job=stream_job,
                    question=current_question,
                    answer=payload.answer,
                    previous_turns=previous_turns,
                ):
                    if item["type"] == "delta":
                        yield _sse_event("delta", {"target": "feedback", "text": item["text"]})
                    elif item["type"] == "progress":
                        yield _sse_event("progress", {"message": item["message"]})
                    elif item["type"] == "result":
                        review = item["review"]

                if review is None:
                    raise RuntimeError("HR interview answer review failed")

                stream_db.add(
                    HrInterviewAnswer(
                        session_id=stream_session.id,
                        question=current_question,
                        answer=payload.answer,
                        score=review.score,
                        source=review.source,
                        focus=stream_session.current_focus,
                        feedback=review.feedback,
                        strengths=review.strengths,
                        weaknesses=review.weaknesses,
                        suggestions=review.suggestions,
                    )
                )
                stream_session.answered_count += 1
                stream_session.total_score += review.score

                next_question = None
                yield _sse_event("progress", {"message": "面试官正在判断本轮回答状态。"})
                attitude = assess_hr_answer_attitude(
                    resume=stream_resume,
                    job=stream_job,
                    question=current_question,
                    answer=payload.answer,
                    previous_turns=previous_turns,
                )
                termination_reason = attitude.reason if attitude.should_terminate else None
                if termination_reason or stream_session.answered_count >= stream_session.total_questions:
                    stream_session.is_finished = True
                    stream_session.current_question = None
                    stream_session.current_focus = []
                    stream_session.termination_reason = termination_reason
                else:
                    yield _sse_event("progress", {"message": "面试官正在准备下一道追问。"})
                    for item in stream_hr_question(
                        resume=stream_resume,
                        job=stream_job,
                        previous_turns=[
                            *previous_turns,
                            {"question": current_question, "answer": payload.answer, "score": review.score},
                        ],
                        question_index=stream_session.answered_count + 1,
                        total_questions=stream_session.total_questions,
                    ):
                        if item["type"] == "delta":
                            yield _sse_event("delta", {"target": "next_question", "text": item["text"]})
                        elif item["type"] == "progress":
                            yield _sse_event("progress", {"message": item["message"]})
                        elif item["type"] == "result":
                            next_question = item["question"]

                    if next_question:
                        stream_session.current_question = next_question.question
                        stream_session.current_focus = next_question.focus
                        stream_session.source = next_question.source
                    else:
                        stream_session.is_finished = True
                        stream_session.current_question = None
                        stream_session.current_focus = []

                stream_db.commit()
                yield _sse_event(
                    "result",
                    {
                        "session_id": stream_session.id,
                        "score": review.score,
                        "source": review.source,
                        "feedback": review.feedback,
                        "strengths": review.strengths,
                        "weaknesses": review.weaknesses,
                        "suggestions": review.suggestions,
                        "next_question": {"question": next_question.question, "focus": next_question.focus}
                        if next_question
                        else None,
                        "answered_count": stream_session.answered_count,
                        "total_questions": stream_session.total_questions,
                        "is_finished": stream_session.is_finished,
                        "termination_reason": termination_reason,
                        "pass_score": settings.interview_pass_score,
                        "passed": (
                            _passed(_average_score(stream_session.total_score, stream_session.answered_count))
                            and not termination_reason
                        )
                        if stream_session.is_finished
                        else None,
                    },
                )
            except Exception as exc:
                stream_db.rollback()
                yield _sse_event("error", {"message": f"岗位 HR 面试反馈生成失败：{exc}"})

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/hr-sessions/{session_id}/report", response_model=HrInterviewReport)
def get_hr_interview_report(session_id: int, db: Session = Depends(get_db)) -> HrInterviewReport:
    session = db.get(HrInterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="HR interview session not found")
    resume = _get_resume_or_404(db, session.resume_id)
    job = _get_job_or_404(db, session.job_id)
    return _build_hr_interview_report(db, session, resume, job)


@router.get("/hr-sessions", response_model=list[HrInterviewSessionSummary])
def list_hr_interview_sessions(db: Session = Depends(get_db)) -> list[HrInterviewSessionSummary]:
    sessions = list(
        db.scalars(
            select(HrInterviewSession)
            .order_by(HrInterviewSession.created_at.desc(), HrInterviewSession.id.desc())
            .limit(20)
        ).all()
    )
    summaries: list[HrInterviewSessionSummary] = []
    for session in sessions:
        resume = db.get(Resume, session.resume_id)
        job = db.get(JobPost, session.job_id)
        if resume is None or job is None:
            continue
        average_score = _average_score(session.total_score, session.answered_count)
        termination_reason = _session_termination_reason(db, session)
        summaries.append(
            HrInterviewSessionSummary(
                session_id=session.id,
                context=_hr_context(resume, job),
                answered_count=session.answered_count,
                total_questions=session.total_questions,
                average_score=average_score,
                is_finished=session.is_finished,
                pass_score=settings.interview_pass_score,
                passed=(_passed(average_score) and not termination_reason)
                if session.is_finished and session.answered_count
                else None,
                termination_reason=termination_reason,
                created_at=session.created_at.isoformat() if session.created_at else "",
            )
        )
    return summaries


def _build_hr_interview_report(
    db: Session,
    session: HrInterviewSession,
    resume: Resume,
    job: JobPost,
) -> HrInterviewReport:
    answers = list(
        db.scalars(
            select(HrInterviewAnswer)
            .where(HrInterviewAnswer.session_id == session.id)
            .order_by(HrInterviewAnswer.id)
        ).all()
    )
    average_score = _average_score(session.total_score, session.answered_count)
    termination_reason = session.termination_reason or _termination_reason_from_answers(answers)
    return HrInterviewReport(
        session_id=session.id,
        context=_hr_context(resume, job),
        answered_count=session.answered_count,
        total_questions=session.total_questions,
        average_score=average_score,
        is_finished=session.is_finished,
        pass_score=settings.interview_pass_score,
        passed=(_passed(average_score) and not termination_reason) if session.is_finished and session.answered_count else None,
        termination_reason=termination_reason,
        recommendation=build_hr_recommendation(average_score),
        answers=[
            HrInterviewReportItem(
                question=item.question,
                answer=item.answer,
                score=item.score,
                source=item.source,
                focus=item.focus or [],
                feedback=item.feedback,
                strengths=item.strengths,
                weaknesses=item.weaknesses,
                suggestions=item.suggestions,
            )
            for item in answers
        ],
    )

def _get_resume_or_404(db: Session, resume_id: int) -> Resume:
    resume = db.get(Resume, resume_id)
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return resume


def _get_job_or_404(db: Session, job_id: int) -> JobPost:
    job = db.get(JobPost, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job post not found")
    return job


def _hr_context(resume: Resume, job: JobPost) -> HrInterviewContextRead:
    return HrInterviewContextRead(
        resume_id=resume.id,
        resume_filename=resume.filename,
        job_id=job.id,
        job_title=job.title,
        company=job.company,
        city=job.city,
        skills=job.skills or [],
    )


def _hr_previous_turns(db: Session, session_id: int) -> list[dict[str, object]]:
    answers = db.scalars(
        select(HrInterviewAnswer).where(HrInterviewAnswer.session_id == session_id).order_by(HrInterviewAnswer.id)
    ).all()
    return [
        {
            "question": answer.question,
            "answer": answer.answer,
            "score": answer.score,
            "feedback": answer.feedback,
        }
        for answer in answers
    ]


def _average_score(total_score: int, answered_count: int) -> float:
    return round(total_score / answered_count, 1) if answered_count else 0.0


def _passed(average_score: float) -> bool:
    return average_score >= settings.interview_pass_score


def _negative_attitude_reason(answer: str) -> str | None:
    return heuristic_hr_attitude_reason(answer)


def _termination_reason_from_answers(answers: list[HrInterviewAnswer]) -> str | None:
    if not answers:
        return None
    return _negative_attitude_reason(answers[-1].answer)


def _session_termination_reason(db: Session, session: HrInterviewSession) -> str | None:
    if session.termination_reason:
        return session.termination_reason
    last_answer = db.scalars(
        select(HrInterviewAnswer)
        .where(HrInterviewAnswer.session_id == session.id)
        .order_by(HrInterviewAnswer.id.desc())
        .limit(1)
    ).first()
    if last_answer is None:
        return None
    return _negative_attitude_reason(last_answer.answer)


def _sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
