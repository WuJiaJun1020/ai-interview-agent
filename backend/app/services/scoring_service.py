from app.core.config import settings
from app.services.llm_scoring import score_answer_with_llm
from app.services.scoring import ScoreResult, score_answer


def score_interview_answer(
    question: str,
    answer: str,
    standard_answer: str,
    rubric: list[str],
    question_type: str = "short_answer",
    correct_answer: str | None = None,
) -> ScoreResult:
    if question_type in {"single_choice", "multiple_choice"}:
        return _score_choice(answer, standard_answer, rubric, correct_answer, question_type)

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
                strengths=fallback.strengths,
                weaknesses=fallback.weaknesses,
                suggestions=fallback.suggestions,
                source="mock",
            )

    return score_answer(answer, standard_answer, rubric)


def _score_choice(
    answer: str,
    standard_answer: str,
    rubric: list[str],
    correct_answer: str | None,
    question_type: str,
) -> ScoreResult:
    normalized_answer = _normalize_choice_answer(answer)
    normalized_correct = _normalize_choice_answer(correct_answer or standard_answer)
    is_correct = normalized_answer == normalized_correct
    score = 100 if is_correct else 0
    matched_rubric = rubric if is_correct else []
    missing_rubric = [] if is_correct else rubric
    type_label = "多选题" if question_type == "multiple_choice" else "选择题"
    return ScoreResult(
        score=score,
        matched_rubric=matched_rubric,
        missing_rubric=missing_rubric,
        feedback=f"{type_label}作答正确，已经掌握该知识点。" if is_correct else f"{type_label}作答不正确，请对照解析复盘关键概念。",
        strengths=[f"{type_label}作答正确，能够识别关键概念。"] if is_correct else [f"已完成{type_label}作答。"],
        weaknesses=["暂未发现明显问题。"] if is_correct else ["当前选项与标准答案不一致。"],
        suggestions=["继续练习更高难度题目。"] if is_correct else ["先阅读参考解析，再重新比较各选项差异。"],
        source="mock",
    )


def _normalize_choice_answer(value: str) -> str:
    parts = [part.strip().upper() for part in value.replace("，", ",").split(",") if part.strip()]
    if not parts:
        return value.strip().upper()
    return ",".join(sorted(parts))
