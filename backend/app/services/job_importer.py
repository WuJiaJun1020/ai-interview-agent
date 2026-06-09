import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import JobPost

SKILL_KEYWORDS = [
    "Python",
    "FastAPI",
    "Django",
    "Flask",
    "Java",
    "Go",
    "Golang",
    "C++",
    "TypeScript",
    "JavaScript",
    "React",
    "Vue",
    "MySQL",
    "Redis",
    "Docker",
    "Kubernetes",
    "K8s",
    "Linux",
    "Git",
    "HTTP",
    "SQL",
    "Kafka",
    "Spark",
    "Flink",
    "PyTorch",
    "TensorFlow",
    "CUDA",
    "Triton",
    "LLM",
    "Agent",
    "Transformer",
    "大模型",
    "机器学习",
    "深度学习",
    "算法",
    "后端",
    "前端",
    "测试",
    "系统设计",
    "分布式",
    "微服务",
]


@dataclass
class JobImportResult:
    imported_count: int
    created_count: int
    updated_count: int
    skipped_count: int
    failed_count: int
    errors: list[str]
    jobs: list[JobPost]


def import_jobs_jsonl(db: Session, content: bytes, filename: str) -> JobImportResult:
    text = content.decode("utf-8-sig")
    created_jobs: list[JobPost] = []
    created_count = 0
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    errors: list[str] = []
    imported_count = 0

    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        imported_count += 1
        try:
            item = json.loads(line)
            if not isinstance(item, dict):
                raise ValueError("JSONL line must be an object")
            job = _build_job_post(item)
            exists = db.scalar(select(JobPost).where(JobPost.content_hash == job.content_hash))
            if exists is not None:
                _update_existing_job(exists, job)
                db.commit()
                db.refresh(exists)
                created_jobs.append(exists)
                updated_count += 1
                continue
            db.add(job)
            db.commit()
            db.refresh(job)
            created_jobs.append(job)
            created_count += 1
        except Exception as exc:
            db.rollback()
            failed_count += 1
            if len(errors) < 20:
                errors.append(f"第 {line_number} 行导入失败：{exc}")

    return JobImportResult(
        imported_count=imported_count,
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        failed_count=failed_count,
        errors=errors,
        jobs=created_jobs,
    )


def _build_job_post(item: dict[str, Any]) -> JobPost:
    source_name = _clean_inline(item.get("source")) or "jsonl"
    company = _clean_inline(item.get("company")) or "未知公司"
    job_id = _clean_inline(item.get("job_id"))
    title = _clean_inline(item.get("title"))
    if not title:
        raise ValueError("缺少 title 字段")

    city = _clean_inline(item.get("city")) or None
    category = _clean_inline(item.get("category")) or None
    job_type = _clean_inline(item.get("job_type"))
    batch = _clean_inline(item.get("batch"))
    department = _clean_inline(item.get("department"))
    source_url = _clean_inline(item.get("url")) or "about:blank"
    description = _join_text([item.get("description"), item.get("responsibilities")])
    requirements = _join_text([item.get("requirements")])
    raw_text = _clean_multiline(item.get("raw_text")) or _join_text(
        [
            f"公司：{company}",
            f"来源：{source_name}",
            f"岗位：{title}",
            f"岗位 ID：{job_id}" if job_id else "",
            f"城市：{city}" if city else "",
            f"岗位类型：{job_type}" if job_type else "",
            f"方向：{category}" if category else "",
            f"批次：{batch}" if batch else "",
            f"部门/业务：{department}" if department else "",
            description,
            requirements,
            source_url,
        ]
    )
    skills = _extract_skills(raw_text)
    content_hash = hashlib.sha256(
        f"{source_name}|{company}|{job_id}|{title}|{source_url}".encode("utf-8"),
    ).hexdigest()

    return JobPost(
        source_name=source_name[:100],
        source_url=source_url[:500],
        company=company[:100],
        title=title[:255],
        city=city[:100] if city else None,
        job_family=(category or _guess_job_family(title, raw_text)),
        seniority=_guess_seniority(job_type, batch, title, raw_text),
        description=description or raw_text[:1200],
        requirements=requirements or raw_text[:1200],
        skills=skills,
        raw_text=raw_text,
        content_hash=content_hash,
    )


def _join_text(values: list[Any]) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, list):
            parts.extend(_clean_multiline(item) for item in value)
        else:
            parts.append(_clean_multiline(value))
    return "\n".join(part for part in parts if part)


def _clean_inline(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _clean_multiline(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t\f\v]+", " ", line).strip() for line in text.split("\n")]
    compact_lines: list[str] = []
    previous_blank = False
    for line in lines:
        if not line:
            if not previous_blank and compact_lines:
                compact_lines.append("")
            previous_blank = True
            continue
        compact_lines.append(line)
        previous_blank = False
    return "\n".join(compact_lines).strip()


def _update_existing_job(existing: JobPost, fresh: JobPost) -> None:
    for field in (
        "source_name",
        "source_url",
        "company",
        "title",
        "city",
        "job_family",
        "seniority",
        "description",
        "requirements",
        "skills",
        "raw_text",
    ):
        setattr(existing, field, getattr(fresh, field))


def _extract_skills(text: str) -> list[str]:
    skills: list[str] = []
    for skill in SKILL_KEYWORDS:
        if re.search(re.escape(skill), text, re.IGNORECASE):
            skills.append(skill)
    return skills


def _guess_job_family(title: str, text: str) -> str | None:
    full = f"{title}\n{text}"
    if any(word in full for word in ("后端", "服务端", "Python", "Java", "Go")):
        return "后端开发"
    if any(word in full for word in ("算法", "机器学习", "深度学习", "推荐", "大模型")):
        return "算法/AI"
    if any(word in full for word in ("前端", "React", "Vue")):
        return "前端开发"
    if any(word in full for word in ("测试", "质量")):
        return "测试开发"
    return None


def _guess_seniority(job_type: str, batch: str, title: str, text: str) -> str | None:
    full = f"{job_type}\n{batch}\n{title}\n{text}"
    if any(word in full.lower() for word in ("intern", "internship")) or any(word in full for word in ("实习", "校招", "应届")):
        return "实习/校招"
    if any(word in full for word in ("高级", "专家", "架构师", "5年", "五年")):
        return "高级"
    if any(word in full for word in ("3年", "三年", "中级")):
        return "中级"
    return "初级"
