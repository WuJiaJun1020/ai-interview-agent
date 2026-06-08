import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.question import Question
from app.schemas.practice import PracticeAnswerCreate, PracticeAnswerResult
from app.schemas.question import QuestionRead
from app.services.scoring_service import score_interview_answer

router = APIRouter(prefix="/api/practice", tags=["practice"])


@router.get("/question", response_model=QuestionRead)
def get_practice_question(
    category: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> Question:
    statement = select(Question)
    if category:
        statement = statement.where(Question.category == category)
    if difficulty:
        statement = statement.where(Question.difficulty == difficulty)

    question = db.scalar(statement.order_by(func.random()).limit(1))
    if question is None:
        raise HTTPException(status_code=404, detail="No question found")
    return question


@router.post("/answer", response_model=PracticeAnswerResult)
def submit_practice_answer(
    payload: PracticeAnswerCreate,
    db: Session = Depends(get_db),
) -> PracticeAnswerResult:
    question = db.get(Question, payload.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    result = score_interview_answer(
        question.question,
        payload.answer,
        question.standard_answer,
        question.rubric,
        question.question_type,
        question.correct_answer,
    )

    return _build_practice_result(question, result)


@router.post("/answer/stream")
def submit_practice_answer_stream(
    payload: PracticeAnswerCreate,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    question = db.get(Question, payload.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    def events() -> Iterator[str]:
        yield _sse_event("progress", {"message": "已收到答案，正在准备评分。"})
        yield _sse_event("progress", {"message": "正在调用评分服务，请稍候。"})
        result = score_interview_answer(
            question.question,
            payload.answer,
            question.standard_answer,
            question.rubric,
            question.question_type,
            question.correct_answer,
        )
        yield _sse_event("result", _build_practice_result(question, result).model_dump())

    return StreamingResponse(events(), media_type="text/event-stream")


def _build_practice_result(question: Question, result) -> PracticeAnswerResult:
    return PracticeAnswerResult(
        question=QuestionRead.model_validate(question),
        score=result.score,
        source=result.source,
        feedback=result.feedback,
        strengths=result.strengths,
        weaknesses=result.weaknesses,
        suggestions=result.suggestions,
        matched_rubric=result.matched_rubric,
        missing_rubric=result.missing_rubric,
        standard_answer=question.standard_answer,
    )


def _sse_event(event: str, payload: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
