from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("/status")
def config_status() -> dict[str, str | bool]:
    scoring_mode = settings.scoring_mode.lower()
    return {
        "scoring_mode": scoring_mode,
        "llm_enabled": scoring_mode == "llm",
        "openai_configured": bool(settings.openai_api_key),
        "openai_model": settings.openai_model,
    }
