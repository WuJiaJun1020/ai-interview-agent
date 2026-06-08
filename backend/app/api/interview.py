from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.interview import InterviewAnswer, InterviewSession
from app.models.question import Question
from app.schemas.interview import (
    InterviewAnswerCreate,
    InterviewAnswerResult,
    InterviewReport,
    InterviewStartCreate,
    InterviewStartResult,
)
from app.schemas.question import QuestionRead
from app.services.scoring_service import score_interview_answer
from app.services.seed_questions import seed_questions

router = APIRouter(prefix="/api/interview", tags=["interview"])


@router.post("/sessions", response_model=InterviewStartResult, status_code=201)
def start_interview(payload: InterviewStartCreate, db: Session = Depends(get_db)) -> InterviewStartResult:
    question = _pick_question(db, payload.category, payload.difficulty)
    if question is None:
        seed_questions(db)
        question = _pick_question(db, payload.category, payload.difficulty)
    if question is None:
        raise HTTPException(status_code=404, detail="No question found")

    session = InterviewSession(
        category=payload.category,
        difficulty=payload.difficulty,
        total_questions=payload.total_questions,
        current_question_id=question.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    return InterviewStartResult(
        session_id=session.id,
        current_question=QuestionRead.model_validate(question),
        answered_count=session.answered_count,
        total_questions=session.total_questions,
        is_finished=session.is_finished,
    )


@router.post("/sessions/{session_id}/answer", response_model=InterviewAnswerResult)
def submit_interview_answer(
    session_id: int,
    payload: InterviewAnswerCreate,
    db: Session = Depends(get_db),
) -> InterviewAnswerResult:
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")
    if session.is_finished:
        raise HTTPException(status_code=400, detail="Interview session is finished")

    question = db.get(Question, session.current_question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Current question not found")

    score_result = score_interview_answer(
        question.question,
        payload.answer,
        question.standard_answer,
        question.rubric,
    )
    db.add(
        InterviewAnswer(
            session_id=session.id,
            question_id=question.id,
            answer=payload.answer,
            score=score_result.score,
            feedback=score_result.feedback,
        )
    )

    session.answered_count += 1
    session.total_score += score_result.score

    next_question = None
    if session.answered_count >= session.total_questions:
        session.is_finished = True
        session.current_question_id = None
    else:
        next_question = _pick_question(db, session.category, session.difficulty, exclude_id=question.id)
        session.current_question_id = next_question.id if next_question else None
        session.is_finished = next_question is None

    db.commit()

    return InterviewAnswerResult(
        session_id=session.id,
        score=score_result.score,
        feedback=score_result.feedback,
        standard_answer=question.standard_answer,
        next_question=QuestionRead.model_validate(next_question) if next_question else None,
        answered_count=session.answered_count,
        total_questions=session.total_questions,
        is_finished=session.is_finished,
    )


@router.get("/sessions/{session_id}/report", response_model=InterviewReport)
def get_interview_report(session_id: int, db: Session = Depends(get_db)) -> InterviewReport:
    session = db.get(InterviewSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found")

    average_score = (
        round(session.total_score / session.answered_count, 1) if session.answered_count else 0.0
    )
    return InterviewReport(
        session_id=session.id,
        answered_count=session.answered_count,
        total_questions=session.total_questions,
        average_score=average_score,
        is_finished=session.is_finished,
        recommendation=_recommendation(average_score),
    )


def _pick_question(
    db: Session,
    category: str | None,
    difficulty: str | None,
    exclude_id: int | None = None,
) -> Question | None:
    statement = select(Question)
    if category:
        statement = statement.where(Question.category == category)
    if difficulty:
        statement = statement.where(Question.difficulty == difficulty)
    if exclude_id:
        statement = statement.where(Question.id != exclude_id)
    return db.scalar(statement.order_by(func.random()).limit(1))


def _recommendation(average_score: float) -> str:
    if average_score >= 80:
        return "整体表现较好，可以继续练习更高难度题目。"
    if average_score >= 60:
        return "基础已经具备，建议补齐回答结构和关键细节。"
    return "建议先复习基础概念，再用题库进行针对性练习。"
