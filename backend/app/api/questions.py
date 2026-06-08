from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.question import Question
from app.schemas.question import QuestionCreate, QuestionRead, QuestionUpdate
from app.services.seed_questions import seed_questions

router = APIRouter(prefix="/api/questions", tags=["questions"])


@router.post("", response_model=QuestionRead, status_code=201)
def create_question(payload: QuestionCreate, db: Session = Depends(get_db)) -> Question:
    question = Question(**payload.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.get("", response_model=list[QuestionRead])
def list_questions(
    category: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Question]:
    statement = select(Question)
    if category:
        statement = statement.where(Question.category == category)
    if difficulty:
        statement = statement.where(Question.difficulty == difficulty)
    return list(db.scalars(statement.order_by(Question.id)).all())


@router.post("/seed")
def seed_question_bank(db: Session = Depends(get_db)) -> dict[str, int]:
    created_count = seed_questions(db)
    return {"created": created_count}


@router.get("/{question_id}", response_model=QuestionRead)
def get_question(question_id: int, db: Session = Depends(get_db)) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.put("/{question_id}", response_model=QuestionRead)
def update_question(
    question_id: int,
    payload: QuestionUpdate,
    db: Session = Depends(get_db),
) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    for field, value in payload.model_dump().items():
        setattr(question, field, value)

    db.commit()
    db.refresh(question)
    return question


@router.delete("/{question_id}", status_code=204)
def delete_question(question_id: int, db: Session = Depends(get_db)) -> None:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")

    db.delete(question)
    db.commit()
