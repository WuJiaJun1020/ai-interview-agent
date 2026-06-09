import json
import re
from dataclasses import dataclass
from collections.abc import Iterator
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.models.job import JobPost
from app.models.resume import Resume


@dataclass
class HrQuestion:
    question: str
    focus: list[str]
    source: str


@dataclass
class HrAnswerReview:
    score: int
    feedback: str
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    source: str


def generate_hr_question(
    resume: Resume,
    job: JobPost,
    previous_turns: list[dict[str, Any]],
    question_index: int,
    total_questions: int,
) -> HrQuestion:
    if settings.scoring_mode.lower() == "llm" and settings.llm_api_key:
        try:
            return _generate_hr_question_with_llm(resume, job, previous_turns, question_index, total_questions)
        except Exception:
            return _generate_hr_question_with_mock(resume, job, previous_turns, question_index, total_questions)

    return _generate_hr_question_with_mock(resume, job, previous_turns, question_index, total_questions)


def stream_hr_question(
    resume: Resume,
    job: JobPost,
    previous_turns: list[dict[str, Any]],
    question_index: int,
    total_questions: int,
) -> Iterator[dict[str, Any]]:
    if settings.scoring_mode.lower() == "llm" and settings.llm_api_key:
        try:
            yield from _stream_hr_question_with_llm(resume, job, previous_turns, question_index, total_questions)
            return
        except Exception as exc:
            yield {"type": "progress", "message": f"LLM 流式生成暂不可用，已回退本地面试官：{exc}"}

    question = _generate_hr_question_with_mock(resume, job, previous_turns, question_index, total_questions)
    yield from _mock_delta_events(question.question)
    yield {"type": "result", "question": question}


def review_hr_answer(
    resume: Resume,
    job: JobPost,
    question: str,
    answer: str,
    previous_turns: list[dict[str, Any]],
) -> HrAnswerReview:
    if settings.scoring_mode.lower() == "llm" and settings.llm_api_key:
        try:
            return _review_hr_answer_with_llm(resume, job, question, answer, previous_turns)
        except Exception as exc:
            fallback = _review_hr_answer_with_mock(resume, job, question, answer)
            fallback.feedback = f"{fallback.feedback}\n\nLLM 面试官暂不可用，已使用本地 mock 反馈：{exc}"
            return fallback

    return _review_hr_answer_with_mock(resume, job, question, answer)


def stream_hr_answer_review(
    resume: Resume,
    job: JobPost,
    question: str,
    answer: str,
    previous_turns: list[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    if settings.scoring_mode.lower() == "llm" and settings.llm_api_key:
        try:
            yield from _stream_hr_answer_review_with_llm(resume, job, question, answer, previous_turns)
            return
        except Exception as exc:
            yield {"type": "progress", "message": f"LLM 流式反馈暂不可用，已回退本地评分：{exc}"}

    review = _review_hr_answer_with_mock(resume, job, question, answer)
    yield from _mock_delta_events(review.feedback)
    yield {"type": "result", "review": review}


def build_hr_recommendation(average_score: float) -> str:
    if average_score >= 85:
        return "岗位匹配表达较成熟，可以继续补充业务影响、协作细节和关键指标，让回答更像真实项目复盘。"
    if average_score >= 70:
        return "整体具备岗位相关性，建议把回答结构固定为背景、行动、结果、反思，并补足 JD 中要求的核心技能细节。"
    if average_score >= 55:
        return "建议优先重写简历中的相关项目描述，并准备 2-3 个能覆盖岗位技能要求的项目案例。"
    return "当前回答与岗位要求的贴合度偏弱，建议先梳理岗位关键词、简历证据和基础概念，再进入下一轮岗位面试。"


def _stream_hr_question_with_llm(
    resume: Resume,
    job: JobPost,
    previous_turns: list[dict[str, Any]],
    question_index: int,
    total_questions: int,
) -> Iterator[dict[str, Any]]:
    content = ""
    emitted = ""
    for chunk in _stream_llm_json(
        system=(
            "你是一位技术招聘 HR 和一面面试官。你必须只输出 JSON，不要输出 markdown。"
            "你正在根据候选人的简历和目标岗位 JD 进行模拟面试。"
            "问题要像真实面试官提出的一样具体、自然、可回答，不要一次问太多问题。"
            "JSON 字段为 question, focus。focus 必须是字符串数组。"
        ),
        payload={
            "resume": _resume_excerpt(resume.content),
            "job": _job_context(job),
            "previous_turns": previous_turns[-6:],
            "question_index": question_index,
            "total_questions": total_questions,
            "task": "生成下一道岗位 HR 面试问题，优先追问简历和 JD 的交集、风险点、项目证据和岗位动机。",
        },
        temperature=0.35,
    ):
        content += chunk
        partial = _partial_json_string(content, "question")
        if partial and len(partial) > len(emitted):
            delta = partial[len(emitted) :]
            emitted = partial
            yield {"type": "delta", "text": delta}

    data = json.loads(content or "{}")
    question_text = str(data.get("question") or emitted).strip()
    focus = _as_string_list(data.get("focus"))
    if not question_text:
        fallback = _generate_hr_question_with_mock(resume, job, previous_turns, question_index, total_questions)
        yield from _mock_delta_events(fallback.question)
        yield {"type": "result", "question": fallback}
        return
    yield {"type": "result", "question": HrQuestion(question=question_text, focus=focus or _default_focus(job), source="llm")}


def _stream_hr_answer_review_with_llm(
    resume: Resume,
    job: JobPost,
    question: str,
    answer: str,
    previous_turns: list[dict[str, Any]],
) -> Iterator[dict[str, Any]]:
    content = ""
    emitted = ""
    for chunk in _stream_llm_json(
        system=(
            "你是一位严谨但友好的技术面试官。你必须只输出 JSON，不要输出 markdown。"
            "请基于目标岗位 JD、候选人简历、当前问题和回答做面试反馈。"
            "JSON 字段为 score, feedback, strengths, weaknesses, suggestions。"
            "score 必须是 0-100 整数；strengths、weaknesses、suggestions 必须是字符串数组。"
        ),
        payload={
            "resume": _resume_excerpt(resume.content),
            "job": _job_context(job),
            "previous_turns": previous_turns[-6:],
            "question": question,
            "answer": answer,
            "score_rule": "高分回答应当贴合岗位要求、有具体项目证据、说明行动和结果，并能体现复盘。",
        },
        temperature=0.2,
    ):
        content += chunk
        partial = _partial_json_string(content, "feedback")
        if partial and len(partial) > len(emitted):
            delta = partial[len(emitted) :]
            emitted = partial
            yield {"type": "delta", "text": delta}

    data = json.loads(content or "{}")
    review = HrAnswerReview(
        score=max(0, min(100, int(data.get("score") or 0))),
        feedback=str(data.get("feedback") or emitted or "已完成岗位面试反馈。"),
        strengths=_as_string_list(data.get("strengths")) or ["回答与岗位要求存在一定关联。"],
        weaknesses=_as_string_list(data.get("weaknesses")) or ["回答还可以补充更多项目证据和量化结果。"],
        suggestions=_as_string_list(data.get("suggestions")) or ["建议按背景、行动、结果、复盘组织回答。"],
        source="llm",
    )
    yield {"type": "result", "review": review}


def _generate_hr_question_with_llm(
    resume: Resume,
    job: JobPost,
    previous_turns: list[dict[str, Any]],
    question_index: int,
    total_questions: int,
) -> HrQuestion:
    data = _call_llm_json(
        system=(
            "你是一位技术招聘 HR 和一面面试官。你必须只输出 JSON，不要输出 markdown。"
            "你正在根据候选人的简历和目标岗位 JD 进行模拟面试。"
            "问题要像真实面试官提出的一样具体、自然、可回答，不要一次问太多问题。"
            "JSON 字段为 question, focus。focus 必须是字符串数组。"
        ),
        payload={
            "resume": _resume_excerpt(resume.content),
            "job": _job_context(job),
            "previous_turns": previous_turns[-6:],
            "question_index": question_index,
            "total_questions": total_questions,
            "task": "生成下一道岗位 HR 面试问题，优先追问简历和 JD 的交集、风险点、项目证据和岗位动机。",
        },
        temperature=0.35,
    )
    question = str(data.get("question") or "").strip()
    focus = _as_string_list(data.get("focus"))
    if not question:
        return _generate_hr_question_with_mock(resume, job, previous_turns, question_index, total_questions)
    return HrQuestion(question=question, focus=focus or _default_focus(job), source="llm")


def _review_hr_answer_with_llm(
    resume: Resume,
    job: JobPost,
    question: str,
    answer: str,
    previous_turns: list[dict[str, Any]],
) -> HrAnswerReview:
    data = _call_llm_json(
        system=(
            "你是一位严谨但友好的技术面试官。你必须只输出 JSON，不要输出 markdown。"
            "请基于目标岗位 JD、候选人简历、当前问题和回答做面试反馈。"
            "JSON 字段为 score, feedback, strengths, weaknesses, suggestions。"
            "score 必须是 0-100 整数；strengths、weaknesses、suggestions 必须是字符串数组。"
        ),
        payload={
            "resume": _resume_excerpt(resume.content),
            "job": _job_context(job),
            "previous_turns": previous_turns[-6:],
            "question": question,
            "answer": answer,
            "score_rule": "高分回答应当贴合岗位要求、有具体项目证据、说明行动和结果，并能体现复盘。",
        },
        temperature=0.2,
    )
    return HrAnswerReview(
        score=max(0, min(100, int(data.get("score") or 0))),
        feedback=str(data.get("feedback") or "已完成岗位面试反馈。"),
        strengths=_as_string_list(data.get("strengths")) or ["回答与岗位要求存在一定关联。"],
        weaknesses=_as_string_list(data.get("weaknesses")) or ["回答还可以补充更多项目证据和量化结果。"],
        suggestions=_as_string_list(data.get("suggestions")) or ["建议按背景、行动、结果、复盘组织回答。"],
        source="llm",
    )


def _generate_hr_question_with_mock(
    resume: Resume,
    job: JobPost,
    previous_turns: list[dict[str, Any]],
    question_index: int,
    total_questions: int,
) -> HrQuestion:
    skills = _job_skills(job)
    resume_hits = [skill for skill in skills if skill.lower() in resume.content.lower()]
    primary_skill = (resume_hits or skills or ["项目经验"])[0]
    missing_skill = next((skill for skill in skills if skill.lower() not in resume.content.lower()), None)

    templates = [
        f"你为什么想投递 {job.company} 的 {job.title}？请结合你简历里最相关的一段经历说明匹配点。",
        f"岗位要求里提到了 {primary_skill}。请讲一个你在项目中实际使用 {primary_skill} 的场景，包括你负责的部分和结果。",
        f"如果入职后需要快速熟悉这个岗位的业务和技术栈，你会如何安排前两周的学习和产出？",
        f"请复盘一次你在项目中遇到的技术难点或排查问题的经历，重点说清楚判断过程和取舍。",
    ]
    if missing_skill:
        templates.append(f"JD 中还提到了 {missing_skill}，但你的简历体现不多。你会如何补足这个能力，并在面试中证明自己能胜任？")

    used_questions = {str(turn.get("question") or "") for turn in previous_turns}
    for offset in range(len(templates)):
        question = templates[(question_index - 1 + offset) % len(templates)]
        if question not in used_questions:
            return HrQuestion(question=question, focus=_default_focus(job), source="mock")

    return HrQuestion(
        question=f"最后请你总结一下，为什么你适合 {job.title}，以及入职后最能立刻贡献价值的地方是什么？",
        focus=["岗位动机", "简历证据", "短期贡献"],
        source="mock",
    )


def _review_hr_answer_with_mock(resume: Resume, job: JobPost, question: str, answer: str) -> HrAnswerReview:
    skills = _job_skills(job)
    answer_lower = answer.lower()
    hits = [skill for skill in skills if skill.lower() in answer_lower]
    has_number = bool(re.search(r"\d+%|\d+ms|\d+qps|\d+人|\d+次|\d+", answer, flags=re.IGNORECASE))
    has_project_signal = bool(re.search(r"项目|负责|实现|优化|排查|上线|协作|复盘", answer))
    has_result_signal = bool(re.search(r"结果|提升|降低|减少|完成|上线|稳定", answer))

    score = 45 + min(len(hits), 4) * 8
    if has_project_signal:
        score += 14
    if has_result_signal:
        score += 10
    if has_number:
        score += 8
    if len(answer.strip()) >= 160:
        score += 8
    score = max(0, min(100, score))

    strengths = []
    if hits:
        strengths.append(f"回答命中了岗位技能：{'、'.join(hits[:5])}。")
    if has_project_signal:
        strengths.append("回答包含项目或职责信息，具备进一步追问的基础。")
    if has_result_signal or has_number:
        strengths.append("回答开始体现结果意识，适合继续补充影响范围。")
    if not strengths:
        strengths.append("已围绕当前问题给出基本回答。")

    weaknesses = []
    if not hits:
        weaknesses.append("回答中岗位关键词较少，和 JD 的连接还不够明确。")
    if not has_project_signal:
        weaknesses.append("缺少具体项目场景，面试官较难判断真实参与度。")
    if not has_number:
        weaknesses.append("缺少量化指标或结果，对说服力有影响。")

    suggestions = [
        "下一版回答可以按 STAR 结构组织：背景、任务、行动、结果。",
        f"建议主动连接 {job.title} 的岗位要求，说明自己能解决什么具体问题。",
    ]
    return HrAnswerReview(
        score=score,
        feedback="已根据目标岗位 JD 和简历内容完成本轮岗位面试反馈。",
        strengths=strengths,
        weaknesses=weaknesses or ["暂未发现明显短板，可以继续提高回答的结构化程度。"],
        suggestions=suggestions,
        source="mock",
    )


def _call_llm_json(system: str, payload: dict[str, Any], temperature: float) -> dict[str, Any]:
    if not settings.llm_api_key:
        raise RuntimeError("OPENAI_API_KEY or DASHSCOPE_API_KEY is not configured")
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.openai_base_url,
        timeout=settings.llm_timeout_seconds,
    )
    request_payload: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    if settings.llm_enable_thinking:
        request_payload["extra_body"] = {"enable_thinking": True}

    response = client.chat.completions.create(**request_payload)
    return json.loads(response.choices[0].message.content or "{}")


def _stream_llm_json(system: str, payload: dict[str, Any], temperature: float) -> Iterator[str]:
    if not settings.llm_api_key:
        raise RuntimeError("OPENAI_API_KEY or DASHSCOPE_API_KEY is not configured")
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.openai_base_url,
        timeout=settings.llm_timeout_seconds,
    )
    request_payload: dict[str, Any] = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "stream": True,
    }
    if settings.llm_enable_thinking:
        request_payload["extra_body"] = {"enable_thinking": True}

    for chunk in client.chat.completions.create(**request_payload):
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            yield delta


def _partial_json_string(content: str, key: str) -> str:
    marker = f'"{key}"'
    key_index = content.find(marker)
    if key_index < 0:
        return ""
    colon_index = content.find(":", key_index + len(marker))
    if colon_index < 0:
        return ""
    quote_index = content.find('"', colon_index + 1)
    if quote_index < 0:
        return ""

    chars: list[str] = []
    index = quote_index + 1
    while index < len(content):
        char = content[index]
        if char == '"':
            break
        if char == "\\":
            next_index = index + 1
            if next_index >= len(content):
                break
            escaped = content[next_index]
            if escaped == "u":
                hex_value = content[next_index + 1 : next_index + 5]
                if len(hex_value) < 4:
                    break
                try:
                    chars.append(chr(int(hex_value, 16)))
                except ValueError:
                    chars.append(f"\\u{hex_value}")
                index = next_index + 5
                continue
            chars.append(_decode_escaped_char(escaped))
            index = next_index + 1
            continue
        chars.append(char)
        index += 1
    return "".join(chars)


def _decode_escaped_char(char: str) -> str:
    return {"n": "\n", "r": "\r", "t": "\t", '"': '"', "\\": "\\"}.get(char, char)


def _mock_delta_events(text: str) -> Iterator[dict[str, Any]]:
    for part in re.split(r"(?<=[。！？!?])", text):
        if part:
            yield {"type": "delta", "text": part}


def _resume_excerpt(content: str) -> str:
    return str(content or "")[:9000]


def _job_context(job: JobPost) -> dict[str, Any]:
    return {
        "title": job.title,
        "company": job.company,
        "city": job.city,
        "job_family": job.job_family,
        "seniority": job.seniority,
        "skills": job.skills or [],
        "description": (job.description or "")[:3000],
        "requirements": (job.requirements or "")[:3000],
    }


def _job_skills(job: JobPost) -> list[str]:
    skills = [str(skill).strip() for skill in (job.skills or []) if str(skill).strip()]
    if skills:
        return skills
    text = f"{job.title} {job.description} {job.requirements}".lower()
    candidates = ["Python", "FastAPI", "MySQL", "Redis", "Docker", "Linux", "Git", "HTTP", "算法", "系统设计"]
    return [skill for skill in candidates if skill.lower() in text] or ["项目经验"]


def _default_focus(job: JobPost) -> list[str]:
    return ["岗位动机", "项目证据", *_job_skills(job)[:3]][:5]


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
