from app.core.config import settings
from app.services.llm_scoring import score_answer_with_llm
from app.services.scoring import ScoreResult, score_answer


def score_interview_answer(
    question: str,
    answer: str,
    standard_answer: str,
    rubric: list[str],
) -> ScoreResult:
    if settings.scoring_mode.lower() == "llm":
        try:
            return score_answer_with_llm(question, answer, standard_answer, rubric)
        except Exception as exc:
            fallback = score_answer(answer, standard_answer, rubric)
            return ScoreResult(
                score=fallback.score,
                matched_rubric=fallback.matched_rubric,
                missing_rubric=fallback.missing_rubric,
                feedback=f"{fallback.feedback}（LLM 评分暂不可用，已使用 mock 评分：{exc}）",
                source="mock",
            )

    return score_answer(answer, standard_answer, rubric)
