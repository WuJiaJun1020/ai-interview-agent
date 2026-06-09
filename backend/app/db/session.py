from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import interview  # noqa: F401
    from app.models import job  # noqa: F401
    from app.models import question  # noqa: F401
    from app.models import resume  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_sqlite_questions()
    _migrate_sqlite_resume_analyses()


def _migrate_sqlite_questions() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "questions" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("questions")}
    statements = []
    if "question_type" not in columns:
        statements.append("ALTER TABLE questions ADD COLUMN question_type VARCHAR(50) DEFAULT 'short_answer'")
    if "options" not in columns:
        statements.append("ALTER TABLE questions ADD COLUMN options JSON DEFAULT '[]'")
    if "correct_answer" not in columns:
        statements.append("ALTER TABLE questions ADD COLUMN correct_answer TEXT")

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def _migrate_sqlite_resume_analyses() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "resume_analyses" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("resume_analyses")}
    if "job_recommendations" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE resume_analyses ADD COLUMN job_recommendations JSON DEFAULT '{}'"))
