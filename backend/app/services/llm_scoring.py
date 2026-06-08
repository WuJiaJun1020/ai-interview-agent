import json

from openai import OpenAI

from app.core.config import settings
from app.services.scoring import ScoreResult


def score_answer_with_llm(
    question: str,
    answer: str,
    standard_answer: str,
    rubric: list[str],
) -> ScoreResult:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一个严谨的技术面试评分助手。"
                    "你必须只输出 JSON，不要输出 markdown。"
                    "JSON 字段为 score, feedback, matched_rubric, missing_rubric。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "answer": answer,
                        "standard_answer": standard_answer,
                        "rubric": rubric,
                        "score_rule": "score 为 0 到 100 的整数。",
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content or "{}"
    data = json.loads(content)
    score = max(0, min(100, int(data.get("score", 0))))
    matched_rubric = _as_string_list(data.get("matched_rubric"))
    missing_rubric = _as_string_list(data.get("missing_rubric"))
    feedback = str(data.get("feedback") or "已完成评分。")
    return ScoreResult(
        score=score,
        matched_rubric=matched_rubric,
        missing_rubric=missing_rubric,
        feedback=feedback,
        source="llm",
    )


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
