from dataclasses import dataclass


@dataclass(frozen=True)
class ScoreResult:
    score: int
    matched_rubric: list[str]
    missing_rubric: list[str]
    feedback: str
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
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
    strengths = _build_strengths(score, matched_rubric)
    weaknesses = _build_weaknesses(missing_rubric)
    suggestions = _build_suggestions(score, missing_rubric)
    return ScoreResult(
        score=score,
        matched_rubric=matched_rubric,
        missing_rubric=missing_rubric,
        feedback=feedback,
        strengths=strengths,
        weaknesses=weaknesses,
        suggestions=suggestions,
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


def _build_strengths(score: int, matched_rubric: list[str]) -> list[str]:
    strengths = [f"已覆盖：{item}" for item in matched_rubric[:3]]
    if score >= 80:
        strengths.insert(0, "回答整体完整，和评分点匹配度较高。")
    if not strengths:
        strengths.append("已经提交了回答，可以在此基础上继续补充。")
    return strengths


def _build_weaknesses(missing_rubric: list[str]) -> list[str]:
    if not missing_rubric:
        return ["暂未发现明显缺失的评分点。"]
    return [f"待补充：{item}" for item in missing_rubric[:3]]


def _build_suggestions(score: int, missing_rubric: list[str]) -> list[str]:
    if missing_rubric:
        return ["先按评分点逐条补充答案。", "每个关键点尽量给出一句解释或项目例子。"]
    if score >= 80:
        return ["尝试补充更具体的项目场景。", "可以挑战更高难度或更多题数。"]
    return ["回答时先给结论，再补充原因、场景和例子。"]
