from pathlib import Path
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.config_status import router as config_status_router
from app.api.db_status import router as db_status_router
from app.api.health import router as health_router
from app.api.interview import router as interview_router
from app.api.practice import router as practice_router
from app.api.questions import router as questions_router
from app.core.config import settings
from app.db.session import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
static_dir = Path(__file__).resolve().parent / "static"

app.mount("/static", StaticFiles(directory=static_dir), name="static")
app.include_router(health_router)
app.include_router(config_status_router)
app.include_router(db_status_router)
app.include_router(questions_router)
app.include_router(practice_router)
app.include_router(interview_router)


@app.get("/")
def root() -> FileResponse:
    return FileResponse(static_dir / "index.html")
