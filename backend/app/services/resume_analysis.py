import json
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from app.core.config import settings


@dataclass
class ResumeAnalysisResult:
    source: str
    target_roles: list[str]
    skills: list[str]
    strengths: list[str]
    weaknesses: list[str]
    suggested_categories: list[str]
    suggested_difficulty: str
    interview_focus: list[str]
    job_recommendations: dict[str, Any]
    raw_feedback: str


TECH_KEYWORDS = {
    "Python": ["python", "django", "flask", "pytest", "pandas"],
    "FastAPI": ["fastapi", "pydantic", "uvicorn"],
    "MySQL": ["mysql", "sql", "索引", "事务", "数据库"],
    "Redis": ["redis", "缓存", "分布式锁"],
    "Docker": ["docker", "容器", "镜像"],
    "Linux": ["linux", "shell", "nginx"],
    "Git": ["git", "github", "gitlab"],
    "HTTP": ["http", "rest", "api", "接口"],
    "算法": ["算法", "leetcode", "复杂度"],
    "系统设计": ["系统设计", "架构", "高并发", "微服务"],
}


def analyze_resume_text(content: str, job_context: dict[str, Any] | None = None) -> ResumeAnalysisResult:
    context = job_context or {}
    if settings.scoring_mode.lower() == "llm" and settings.llm_api_key:
        try:
            return _analyze_with_llm(content, context)
        except Exception as exc:
            fallback = _analyze_with_mock(content, context)
            fallback.raw_feedback = f"{fallback.raw_feedback}\n\nLLM 分析暂不可用，已使用 mock 分析：{exc}"
            return fallback

    return _analyze_with_mock(content, context)


def _analyze_with_mock(content: str, job_context: dict[str, Any] | None = None) -> ResumeAnalysisResult:
    job_context = _apply_rule_top_jobs(job_context or {}, source="rule_fallback")
    normalized = content.lower()
    skills = [
        category
        for category, keywords in TECH_KEYWORDS.items()
        if any(keyword.lower() in normalized for keyword in keywords)
    ]
    if not skills:
        skills = ["Python", "MySQL"]

    matched_jobs = (job_context or {}).get("matched_jobs") or []
    roles = [str(job.get("title")) for job in matched_jobs[:3] if isinstance(job, dict) and job.get("title")]
    if not roles:
        roles = _guess_roles(skills)
    suggested_difficulty = _guess_difficulty(content, skills)
    strengths = _guess_strengths(content, skills)
    weaknesses = _guess_weaknesses(content)
    interview_focus = [
        f"{skill} 核心概念和项目落地经验"
        for skill in skills[:5]
    ]
    raw_feedback = (
        "简历已完成基础画像分析。建议优先围绕简历中出现频率较高的技术栈准备项目追问，"
        "同时补充可量化结果、故障排查经历和技术取舍依据。"
    )
    if matched_jobs:
        raw_feedback = (
            f"已结合岗位知识库中的 {len(matched_jobs)} 个相似岗位完成分析。"
            "建议优先选择匹配分更高的真实 JD 准备项目复盘和能力缺口。"
        )
    return ResumeAnalysisResult(
        source="mock",
        target_roles=roles,
        skills=skills,
        strengths=strengths,
        weaknesses=weaknesses,
        suggested_categories=skills[:6],
        suggested_difficulty=suggested_difficulty,
        interview_focus=interview_focus,
        job_recommendations={},
        raw_feedback=raw_feedback,
    )


def _analyze_with_llm(content: str, job_context: dict[str, Any]) -> ResumeAnalysisResult:
    compact_job_context = _compact_job_context_for_llm(job_context)
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.openai_base_url,
        timeout=settings.llm_timeout_seconds,
    )
    request_payload = {
        "model": settings.openai_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一个技术招聘和面试准备顾问。你必须只输出 JSON，不要输出 markdown。"
                    "JSON 字段为 target_roles, skills, strengths, weaknesses, "
                    "suggested_categories, suggested_difficulty, interview_focus, raw_feedback, ranked_jobs。"
                    "target_roles、skills、strengths、weaknesses、suggested_categories、interview_focus 必须是字符串数组。"
                    "suggested_difficulty 只能是 初级、中级、高级 之一。"
                    "ranked_jobs 必须是数组，最多 3 项，每项包含 job_id, rank, match_level, match_score, reasons, risks, resume_improvements。"
                    "match_level 只能是 强匹配、可冲刺、不建议优先 之一；match_score 是 0-100 整数。"
                    "如果提供了岗位知识库检索结果，必须结合简历和 Chroma 召回的 Top 8 真实 JD 选出最终 Top 3；"
                    "不要新增候选之外的岗位，ranked_jobs 必须使用候选里的 job_id。"
                    "只有知识库匹配不足时才可以自由发挥，并在 raw_feedback 中说明。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "resume": content[:9000],
                        "job_knowledge_context": compact_job_context,
                        "known_question_categories": list(TECH_KEYWORDS.keys()),
                        "task": "结合简历和候选 JD 完成一次完整分析：输出岗位画像、面试练习建议，并从候选 JD 中精排 Top 3。",
                    },
                    ensure_ascii=False,
                ),
            },
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    if settings.llm_enable_thinking:
        request_payload["extra_body"] = {"enable_thinking": True}

    response = client.chat.completions.create(**request_payload)
    data = json.loads(response.choices[0].message.content or "{}")
    _apply_ranked_jobs_to_context(job_context, data.get("ranked_jobs"))
    return ResumeAnalysisResult(
        source="llm",
        target_roles=_as_string_list(data.get("target_roles")) or ["后端开发工程师"],
        skills=_as_string_list(data.get("skills")) or ["Python"],
        strengths=_as_string_list(data.get("strengths")) or ["简历具备一定技术项目经历。"],
        weaknesses=_as_string_list(data.get("weaknesses")) or ["建议补充更多量化结果。"],
        suggested_categories=_as_string_list(data.get("suggested_categories")) or ["Python"],
        suggested_difficulty=_normalize_difficulty(str(data.get("suggested_difficulty") or "初级")),
        interview_focus=_as_string_list(data.get("interview_focus")) or ["围绕项目经历准备技术追问。"],
        job_recommendations={},
        raw_feedback=str(data.get("raw_feedback") or "已完成简历分析。"),
    )


def _compact_job_context_for_llm(job_context: dict[str, Any]) -> dict[str, Any]:
    matched_jobs = job_context.get("matched_jobs") or []
    candidates = _compact_job_candidates(matched_jobs[:8])
    return {
        "knowledge_base_used": bool(candidates) and bool(job_context.get("knowledge_base_used")),
        "candidate_count": len(candidates),
        "matched_jobs": candidates,
        "fallback_recommendations": (job_context.get("fallback_recommendations") or [])[:3],
    }


def _compact_job_candidates(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates = []
    for index, job in enumerate(jobs, start=1):
        evidence = job.get("evidence_chunks") or []
        candidates.append(
            {
                "rank": index,
                "job_id": job.get("job_id"),
                "title": job.get("title"),
                "company": job.get("company"),
                "city": job.get("city"),
                "job_family": job.get("job_family"),
                "seniority": job.get("seniority"),
                "rule_score": job.get("match_score"),
                "matched_keywords": (job.get("matched_keywords") or [])[:6],
                "rule_reasons": (job.get("match_reasons") or [])[:2],
                "gaps": (job.get("gaps") or [])[:2],
                "prep_focus": (job.get("prep_focus") or [])[:2],
                "evidence": [
                    {
                        "type": item.get("chunk_type"),
                        "text": str(item.get("text") or "")[:180],
                    }
                    for item in evidence[:2]
                    if isinstance(item, dict)
                ],
            }
        )
    return [candidate for candidate in candidates if candidate.get("job_id")]


def _apply_ranked_jobs_to_context(job_context: dict[str, Any], ranked_jobs: object) -> dict[str, Any]:
    matched_jobs = job_context.get("matched_jobs") or []
    candidates = matched_jobs[:8]
    if not candidates:
        job_context["rerank"] = {"enabled": False, "source": "no_candidates"}
        return job_context
    if not isinstance(ranked_jobs, list):
        return _apply_rule_top_jobs(job_context, source="llm_missing_ranked_jobs")

    jobs_by_id = {str(job.get("job_id")): job for job in candidates if job.get("job_id") is not None}
    selected = []
    for item in ranked_jobs[:3]:
        if not isinstance(item, dict):
            continue
        job = jobs_by_id.get(str(item.get("job_id")))
        if not job:
            continue
        enriched = dict(job)
        enriched["llm_rank"] = int(item.get("rank") or len(selected) + 1)
        enriched["llm_match_level"] = str(item.get("match_level") or "")
        enriched["llm_match_score"] = int(item.get("match_score") or enriched.get("match_score") or 0)
        enriched["llm_reasons"] = _as_string_list(item.get("reasons"))
        enriched["llm_risks"] = _as_string_list(item.get("risks"))
        enriched["llm_resume_improvements"] = _as_string_list(item.get("resume_improvements"))
        if enriched["llm_match_score"]:
            enriched["match_score"] = enriched["llm_match_score"]
        if enriched["llm_reasons"]:
            enriched["match_reasons"] = enriched["llm_reasons"]
        selected.append(enriched)

    if not selected:
        return _apply_rule_top_jobs(job_context, source="llm_invalid_ranked_jobs")

    job_context["matched_jobs"] = selected
    job_context["knowledge_base_used"] = True
    job_context["rerank"] = {
        "enabled": True,
        "source": "llm_analysis",
        "mode": "single_call",
        "candidate_count": len(candidates),
        "selected_count": len(selected),
    }
    return job_context


def _apply_rule_top_jobs(job_context: dict[str, Any], source: str) -> dict[str, Any]:
    matched_jobs = job_context.get("matched_jobs") or []
    if not matched_jobs:
        job_context["rerank"] = {"enabled": False, "source": "skipped"}
        return job_context

    selected = matched_jobs[:3]
    job_context["matched_jobs"] = selected
    job_context["knowledge_base_used"] = bool(selected) and bool(job_context.get("knowledge_base_used"))
    job_context["rerank"] = {
        "enabled": False,
        "source": source,
        "candidate_count": min(len(matched_jobs), 8),
        "selected_count": len(selected),
    }
    return job_context


def _guess_roles(skills: list[str]) -> list[str]:
    roles = []
    if "Python" in skills or "FastAPI" in skills:
        roles.append("Python 后端开发工程师")
    if "FastAPI" in skills or "HTTP" in skills:
        roles.append("Web 后端开发工程师")
    if "系统设计" in skills or "Docker" in skills:
        roles.append("后端工程化/平台开发")
    if "MySQL" in skills and "Redis" in skills:
        roles.append("服务端开发工程师")
    return roles or ["后端开发工程师"]


def _guess_difficulty(content: str, skills: list[str]) -> str:
    project_count = len(re.findall(r"项目|project", content, flags=re.IGNORECASE))
    if len(skills) >= 6 or project_count >= 3:
        return "中级"
    return "初级"


def _guess_strengths(content: str, skills: list[str]) -> list[str]:
    strengths = [f"简历中体现了 {skill} 相关经验。" for skill in skills[:3]]
    if re.search(r"上线|部署|优化|性能|并发|监控", content):
        strengths.append("简历包含工程落地或性能优化相关表述。")
    return strengths or ["简历已提供基础项目和技能信息。"]


def _guess_weaknesses(content: str) -> list[str]:
    weaknesses = []
    if not re.search(r"\d+%|\d+ms|\d+万|\d+人|\d+次|\d+qps", content, flags=re.IGNORECASE):
        weaknesses.append("项目成果缺少量化指标，面试时可能需要补充影响范围和结果。")
    if not re.search(r"难点|挑战|取舍|排查|故障|优化", content):
        weaknesses.append("技术难点和问题排查描述偏少，建议准备 1-2 个可追问案例。")
    return weaknesses or ["暂未发现明显短板，建议继续强化项目细节表达。"]


def _normalize_difficulty(value: str) -> str:
    return value if value in {"初级", "中级", "高级"} else "初级"


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
