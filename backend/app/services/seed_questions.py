import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.question import Question
from app.schemas.question import QuestionCreate

SEED_FILE = Path(__file__).resolve().parents[1] / "data" / "seed_questions.json"


def load_seed_questions() -> list[QuestionCreate]:
    seed_data = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    return [QuestionCreate(**item) for item in seed_data]


def seed_questions(db: Session) -> int:
    created_count = 0

    for payload in load_seed_questions():
        exists = db.scalar(
            select(Question).where(
                Question.category == payload.category,
                Question.difficulty == payload.difficulty,
                Question.question == payload.question,
            )
        )
        if exists is not None:
            continue

        db.add(Question(**payload.model_dump()))
        created_count += 1

    db.commit()
    return created_count
