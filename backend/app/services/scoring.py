from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreResult:
    score: int
    matched_rubric: list[str]
    missing_rubric: list[str]
    feedback: str
    source: str = "mock"


def score_answer(
    answer: str,
    standard_answer: str,
    rubric: list[str],
) -> ScoreResult:
    matched_rubric = [
        item for item in rubric if any(token in answer.lower() for token in _keywords(item))
    ]
    missing_rubric = [item for item in rubric if item not in matched_rubric]
    score = _score(answer, standard_answer, rubric, matched_rubric)
    feedback = _build_feedback(score, matched_rubric, missing_rubric)
    return ScoreResult(
        score=score,
        matched_rubric=matched_rubric,
        missing_rubric=missing_rubric,
        feedback=feedback,
    )


def _keywords(rubric_item: str) -> list[str]:
    words = [word.lower() for word in rubric_item.replace("，", " ").replace("、", " ").split()]
    return [word for word in words if len(word) >= 2]


def _score(
    answer: str,
    standard_answer: str,
    rubric: list[str],
    matched_rubric: list[str],
) -> int:
    if not answer.strip():
        return 0

    rubric_score = int(80 * len(matched_rubric) / max(len(rubric), 1))
    length_score = min(len(answer.strip()) // 10, 10)
    overlap_score = 10 if any(token in answer for token in standard_answer.split()[:5]) else 0
    return min(rubric_score + length_score + overlap_score, 100)


def _build_feedback(
    score: int,
    matched_rubric: list[str],
    missing_rubric: list[str],
) -> str:
    if score >= 80:
        return "回答比较完整，已经覆盖主要评分点。"
    if matched_rubric:
        return "回答有一定基础，但还需要补充遗漏的评分点。"
    if missing_rubric:
        return "回答偏泛泛，需要围绕题目的关键评分点展开。"
    return "回答已收到，可以继续补充更多细节。"
