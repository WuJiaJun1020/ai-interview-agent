import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.job import JobPost

VECTOR_DIMENSIONS = 768
INDEX_VERSION = 1
INDEX_PATH = Path(__file__).resolve().parents[2] / "vector_store" / "job_index.json"
CHROMA_PATH = Path(__file__).resolve().parents[2] / "vector_store" / "chroma"
CHROMA_COLLECTION = "job_posts"


@dataclass
class JobVectorStatus:
    exists: bool
    path: str
    job_count: int = 0
    chunk_count: int = 0
    built_at: str | None = None
    version: int | None = None
    backend: str = "local_hash"
    collection_name: str | None = None
    chroma_available: bool = False
    fallback_path: str | None = None
    error: str | None = None


@dataclass
class JobRecommendation:
    source: str
    job_id: int | None
    title: str
    company: str
    city: str | None
    job_family: str | None
    seniority: str | None
    source_url: str | None
    match_score: int
    match_reasons: list[str]
    gaps: list[str]
    prep_focus: list[str]
    matched_keywords: list[str]
    evidence_chunks: list[dict[str, str]]


@dataclass
class JobRecommendationBundle:
    knowledge_base_used: bool
    matched_jobs: list[JobRecommendation]
    fallback_recommendations: list[JobRecommendation]
    index_status: JobVectorStatus


def rebuild_job_vector_index(db: Session) -> JobVectorStatus:
    jobs = list(db.scalars(select(JobPost).order_by(JobPost.id)).all())
    chunks: list[dict[str, Any]] = []
    for job in jobs:
        chunks.extend(_job_chunks(job))

    fallback_status = _rebuild_local_hash_index(jobs, chunks)
    chroma_status = _rebuild_chroma_index(jobs, chunks)
    if chroma_status.exists:
        return chroma_status
    if chroma_status.error:
        fallback_status.error = chroma_status.error
        fallback_status.chroma_available = chroma_status.chroma_available
    return fallback_status


def _rebuild_local_hash_index(jobs: list[JobPost], chunks: list[dict[str, Any]]) -> JobVectorStatus:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": INDEX_VERSION,
        "built_at": datetime.now().isoformat(timespec="seconds"),
        "job_count": len(jobs),
        "chunk_count": len(chunks),
        "chunks": chunks,
    }
    INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return get_job_vector_status()


def get_job_vector_status() -> JobVectorStatus:
    chroma_status = _get_chroma_status()
    if chroma_status.exists:
        return chroma_status

    fallback_status = _get_local_hash_status()
    if chroma_status.error:
        fallback_status.error = chroma_status.error
        fallback_status.chroma_available = chroma_status.chroma_available
    if fallback_status.exists:
        return fallback_status

    return chroma_status


def _get_local_hash_status() -> JobVectorStatus:
    if not INDEX_PATH.exists():
        return JobVectorStatus(
            exists=False,
            path=str(INDEX_PATH),
            backend="local_hash",
            fallback_path=str(INDEX_PATH),
        )
    try:
        payload = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except Exception:
        return JobVectorStatus(
            exists=False,
            path=str(INDEX_PATH),
            backend="local_hash",
            fallback_path=str(INDEX_PATH),
            error="Local hash index cannot be read",
        )
    return JobVectorStatus(
        exists=True,
        path=str(INDEX_PATH),
        job_count=int(payload.get("job_count") or 0),
        chunk_count=int(payload.get("chunk_count") or 0),
        built_at=payload.get("built_at"),
        version=payload.get("version"),
        backend="local_hash",
        fallback_path=str(INDEX_PATH),
    )


def recommend_jobs_for_resume(db: Session, resume_text: str, limit: int = 6) -> JobRecommendationBundle:
    status = get_job_vector_status()
    db_job_count = int(db.scalar(select(func.count()).select_from(JobPost)) or 0)
    if not status.exists or status.job_count != db_job_count:
        status = rebuild_job_vector_index(db)

    if status.backend == "chroma" and status.exists:
        try:
            return _recommend_jobs_with_chroma(db, resume_text, limit, status)
        except Exception as exc:
            fallback_status = _get_local_hash_status()
            fallback_status.error = f"Chroma query failed: {exc}"
            return _recommend_jobs_with_local_hash(db, resume_text, limit, fallback_status)

    return _recommend_jobs_with_local_hash(db, resume_text, limit, status)


def _recommend_jobs_with_local_hash(
    db: Session,
    resume_text: str,
    limit: int,
    status: JobVectorStatus,
) -> JobRecommendationBundle:
    payload = _load_index()
    chunks = payload.get("chunks", [])
    if not chunks:
        return JobRecommendationBundle(
            knowledge_base_used=False,
            matched_jobs=[],
            fallback_recommendations=_fallback_recommendations(resume_text),
            index_status=status,
        )

    query_vector = _vectorize(_resume_query_text(resume_text))
    scored_chunks: list[tuple[float, dict[str, Any]]] = []
    for chunk in chunks:
        score = _cosine(query_vector, chunk.get("vector") or {})
        if score > 0:
            scored_chunks.append((score * _chunk_weight(str(chunk.get("chunk_type") or "")), chunk))

    aggregate: dict[int, dict[str, Any]] = {}
    for score, chunk in sorted(scored_chunks, key=lambda item: item[0], reverse=True)[:80]:
        job_id = int(chunk["job_id"])
        bucket = aggregate.setdefault(job_id, {"score": 0.0, "chunks": [], "metadata": chunk})
        bucket["score"] += score
        bucket["chunks"].append(chunk)

    top = sorted(aggregate.values(), key=lambda item: item["score"], reverse=True)[:limit]
    matched_jobs = [_build_recommendation(db, resume_text, item) for item in top]
    matched_jobs = [job for job in matched_jobs if job.match_score > 0]
    knowledge_base_used = bool(matched_jobs and matched_jobs[0].match_score >= 28)
    fallback = [] if knowledge_base_used else _fallback_recommendations(resume_text)
    return JobRecommendationBundle(
        knowledge_base_used=knowledge_base_used,
        matched_jobs=matched_jobs if knowledge_base_used else matched_jobs[:3],
        fallback_recommendations=fallback,
        index_status=status,
    )


def _recommend_jobs_with_chroma(
    db: Session,
    resume_text: str,
    limit: int,
    status: JobVectorStatus,
) -> JobRecommendationBundle:
    collection = _get_chroma_collection()
    query = _resume_query_text(resume_text)
    result = collection.query(
        query_texts=[query],
        n_results=min(80, max(limit * 12, limit)),
        include=["metadatas", "documents", "distances"],
    )
    metadatas = result.get("metadatas", [[]])[0]
    documents = result.get("documents", [[]])[0]
    distances = result.get("distances", [[]])[0]
    if not metadatas:
        return JobRecommendationBundle(
            knowledge_base_used=False,
            matched_jobs=[],
            fallback_recommendations=_fallback_recommendations(resume_text),
            index_status=status,
        )

    aggregate: dict[int, dict[str, Any]] = {}
    for metadata, document, distance in zip(metadatas, documents, distances):
        job_id = int(metadata["job_id"])
        chunk_type = str(metadata.get("chunk_type") or "profile")
        similarity = 1 / (1 + max(0.0, float(distance or 0.0)))
        score = similarity * _chunk_weight(chunk_type)
        chunk = {
            **metadata,
            "job_id": job_id,
            "chunk_type": chunk_type,
            "text": document or "",
        }
        bucket = aggregate.setdefault(job_id, {"score": 0.0, "chunks": [], "metadata": chunk})
        bucket["score"] += score
        bucket["chunks"].append(chunk)

    top = sorted(aggregate.values(), key=lambda item: item["score"], reverse=True)[:limit]
    matched_jobs = [_build_recommendation(db, resume_text, item) for item in top]
    matched_jobs = [job for job in matched_jobs if job.match_score > 0]
    knowledge_base_used = bool(matched_jobs and matched_jobs[0].match_score >= 28)
    fallback = [] if knowledge_base_used else _fallback_recommendations(resume_text)
    return JobRecommendationBundle(
        knowledge_base_used=knowledge_base_used,
        matched_jobs=matched_jobs if knowledge_base_used else matched_jobs[:3],
        fallback_recommendations=fallback,
        index_status=status,
    )


def recommendation_bundle_to_json(bundle: JobRecommendationBundle) -> dict[str, Any]:
    return {
        "knowledge_base_used": bundle.knowledge_base_used,
        "matched_jobs": [asdict(item) for item in bundle.matched_jobs],
        "fallback_recommendations": [asdict(item) for item in bundle.fallback_recommendations],
        "index_status": asdict(bundle.index_status),
    }


def _load_index() -> dict[str, Any]:
    if not INDEX_PATH.exists():
        return {}
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def _rebuild_chroma_index(jobs: list[JobPost], chunks: list[dict[str, Any]]) -> JobVectorStatus:
    try:
        collection = _get_chroma_collection(reset=True)
    except Exception as exc:
        return JobVectorStatus(
            exists=False,
            path=str(CHROMA_PATH),
            backend="chroma",
            collection_name=CHROMA_COLLECTION,
            chroma_available=False,
            fallback_path=str(INDEX_PATH),
            error=f"Chroma is unavailable: {exc}",
        )

    if chunks:
        ids = [f"job-{chunk['job_id']}-{chunk['chunk_type']}-{index}" for index, chunk in enumerate(chunks)]
        documents = [str(chunk.get("text") or "") for chunk in chunks]
        metadatas = [_chroma_metadata(chunk) for chunk in chunks]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    built_at = datetime.now().isoformat(timespec="seconds")
    collection.modify(
        metadata={
            "version": INDEX_VERSION,
            "built_at": built_at,
            "job_count": len(jobs),
            "chunk_count": len(chunks),
        }
    )
    return JobVectorStatus(
        exists=True,
        path=str(CHROMA_PATH),
        job_count=len(jobs),
        chunk_count=len(chunks),
        built_at=built_at,
        version=INDEX_VERSION,
        backend="chroma",
        collection_name=CHROMA_COLLECTION,
        chroma_available=True,
        fallback_path=str(INDEX_PATH),
    )


def _get_chroma_status() -> JobVectorStatus:
    try:
        collection = _get_chroma_collection()
    except Exception as exc:
        return JobVectorStatus(
            exists=False,
            path=str(CHROMA_PATH),
            backend="chroma",
            collection_name=CHROMA_COLLECTION,
            chroma_available=False,
            fallback_path=str(INDEX_PATH),
            error=f"Chroma is unavailable: {exc}",
        )

    metadata = collection.metadata or {}
    chunk_count = collection.count()
    job_count = int(metadata.get("job_count") or 0)
    if chunk_count and not job_count:
        job_count = chunk_count
    return JobVectorStatus(
        exists=chunk_count > 0,
        path=str(CHROMA_PATH),
        job_count=job_count,
        chunk_count=chunk_count,
        built_at=metadata.get("built_at"),
        version=int(metadata.get("version") or INDEX_VERSION) if chunk_count else None,
        backend="chroma",
        collection_name=CHROMA_COLLECTION,
        chroma_available=True,
        fallback_path=str(INDEX_PATH),
    )


def _get_chroma_collection(reset: bool = False):
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings
    except Exception as exc:
        raise RuntimeError("chromadb package is not installed") from exc

    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    if reset:
        try:
            client.delete_collection(CHROMA_COLLECTION)
        except Exception:
            pass
    return client.get_or_create_collection(
        name=CHROMA_COLLECTION,
        embedding_function=HashEmbeddingFunction(),
        metadata={"hnsw:space": "cosine"},
    )


class HashEmbeddingFunction:
    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002 - Chroma expects this parameter name.
        return [_dense_hash_vector(text) for text in input]


def _dense_hash_vector(text: str) -> list[float]:
    sparse = _vectorize(text)
    dense = [0.0] * VECTOR_DIMENSIONS
    for key, value in sparse.items():
        dense[int(key)] = float(value)
    return dense


def _chroma_metadata(chunk: dict[str, Any]) -> dict[str, str | int | float | bool | None]:
    allowed_keys = (
        "job_id",
        "title",
        "company",
        "city",
        "job_family",
        "seniority",
        "source_url",
        "chunk_type",
    )
    metadata: dict[str, str | int | float | bool | None] = {}
    for key in allowed_keys:
        value = chunk.get(key)
        if value is None:
            metadata[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            metadata[key] = value
        else:
            metadata[key] = str(value)
    return metadata


def _job_chunks(job: JobPost) -> list[dict[str, Any]]:
    base = {
        "job_id": job.id,
        "title": job.title,
        "company": job.company,
        "city": job.city,
        "job_family": job.job_family,
        "seniority": job.seniority,
        "source_url": job.source_url,
    }
    texts = [
        ("profile", f"{job.company} {job.title} {job.city or ''} {job.job_family or ''} {job.seniority or ''} {' '.join(job.skills or [])}"),
        ("description", job.description or ""),
        ("requirements", job.requirements or ""),
    ]
    chunks = []
    for chunk_type, text in texts:
        cleaned = _clean(text)
        if not cleaned:
            continue
        chunks.append({**base, "chunk_type": chunk_type, "text": cleaned[:4000], "vector": _vectorize(cleaned)})
    return chunks


def _resume_query_text(resume_text: str) -> str:
    lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    signal_lines = [
        line
        for line in lines
        if re.search(r"技能|项目|经历|实习|开发|算法|后端|前端|大模型|Agent|数据库|缓存|部署|优化", line, re.IGNORECASE)
    ]
    return "\n".join(signal_lines or lines)[:6000]


def _vectorize(text: str) -> dict[str, float]:
    tokens = _tokens(text)
    counts = Counter(tokens)
    vector: defaultdict[str, float] = defaultdict(float)
    for token, count in counts.items():
        index = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16) % VECTOR_DIMENSIONS
        vector[str(index)] += math.log1p(count)
    norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
    return {key: round(value / norm, 6) for key, value in vector.items()}


def _tokens(text: str) -> list[str]:
    normalized = _clean(text).lower()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{1,}|[\u4e00-\u9fff]{2,}", normalized)
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]+", normalized))
    for size in (2, 3, 4):
        tokens.extend(chinese[index : index + size] for index in range(max(0, len(chinese) - size + 1)))
    return tokens


def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    if len(left) > len(right):
        left, right = right, left
    return sum(value * float(right.get(key, 0.0)) for key, value in left.items())


def _chunk_weight(chunk_type: str) -> float:
    return {"requirements": 1.25, "profile": 1.15, "description": 1.0}.get(chunk_type, 1.0)


def _build_recommendation(db: Session, resume_text: str, item: dict[str, Any]) -> JobRecommendation:
    metadata = item["metadata"]
    job = db.get(JobPost, int(metadata["job_id"]))
    if job is None:
        return JobRecommendation("knowledge_base", None, "未知岗位", "未知公司", None, None, None, None, 0, [], [], [], [], [])

    resume_tokens = set(_tokens(resume_text))
    job_text = f"{job.title}\n{job.description}\n{job.requirements}\n{' '.join(job.skills or [])}"
    job_tokens = set(_tokens(job_text))
    overlap = sorted(resume_tokens & job_tokens, key=len, reverse=True)
    skill_hits = [skill for skill in (job.skills or []) if skill.lower() in resume_text.lower()]
    matched_keywords = _matched_keywords(skill_hits, overlap)
    score = min(100, round(item["score"] * 140 + len(skill_hits) * 5 + min(len(overlap), 8)))
    reasons = []
    if skill_hits:
        reasons.append(f"技能命中：{'、'.join(skill_hits[:5])}")
    if job.job_family:
        reasons.append(f"岗位方向匹配：{job.job_family}")
    if job.seniority:
        reasons.append(f"岗位级别参考：{job.seniority}")
    if not reasons:
        reasons.append("简历语义与岗位描述存在相似项目/技能信号。")

    gaps = _infer_gaps(resume_text, job)
    prep_focus = _prep_focus(job, skill_hits)
    evidence_chunks = _evidence_chunks(item.get("chunks") or [], matched_keywords)
    return JobRecommendation(
        source="knowledge_base",
        job_id=job.id,
        title=job.title,
        company=job.company,
        city=job.city,
        job_family=job.job_family,
        seniority=job.seniority,
        source_url=job.source_url,
        match_score=score,
        match_reasons=reasons[:4],
        gaps=gaps,
        prep_focus=prep_focus,
        matched_keywords=matched_keywords,
        evidence_chunks=evidence_chunks,
    )


def _matched_keywords(skill_hits: list[str], overlap: list[str]) -> list[str]:
    keywords: list[str] = []
    for item in [*skill_hits, *overlap]:
        value = str(item).strip()
        if len(value) < 2 or len(value) > 24 or value in keywords:
            continue
        keywords.append(value)
        if len(keywords) >= 10:
            break
    return keywords


def _evidence_chunks(chunks: list[dict[str, Any]], keywords: list[str]) -> list[dict[str, str]]:
    evidence = []
    seen = set()
    for chunk in chunks[:6]:
        chunk_type = str(chunk.get("chunk_type") or "profile")
        text = _highlightable_excerpt(str(chunk.get("text") or ""), keywords)
        if not text or (chunk_type, text) in seen:
            continue
        seen.add((chunk_type, text))
        evidence.append(
            {
                "chunk_type": _chunk_type_label(chunk_type),
                "text": text,
            }
        )
        if len(evidence) >= 3:
            break
    return evidence


def _highlightable_excerpt(text: str, keywords: list[str], limit: int = 180) -> str:
    cleaned = _clean(text)
    if not cleaned:
        return ""
    lower = cleaned.lower()
    hit_positions = [lower.find(keyword.lower()) for keyword in keywords if keyword and lower.find(keyword.lower()) >= 0]
    if not hit_positions:
        return cleaned[:limit]
    start = max(0, min(hit_positions) - 40)
    excerpt = cleaned[start : start + limit]
    return f"...{excerpt}" if start > 0 else excerpt


def _chunk_type_label(chunk_type: str) -> str:
    return {
        "profile": "岗位画像",
        "description": "岗位描述",
        "requirements": "岗位要求",
    }.get(chunk_type, "岗位片段")


def _infer_gaps(resume_text: str, job: JobPost) -> list[str]:
    gaps = []
    required_text = job.requirements or job.raw_text or ""
    for keyword in ("Java", "C++", "Go", "Spark", "Flink", "Redis", "MySQL", "Docker", "Kubernetes", "大模型", "算法"):
        if keyword.lower() in required_text.lower() and keyword.lower() not in resume_text.lower():
            gaps.append(f"岗位要求提到 {keyword}，简历中体现较少。")
    if "量化" not in resume_text and not re.search(r"\d+%|\d+ms|\d+qps|\d+万", resume_text, re.IGNORECASE):
        gaps.append("简历项目成果量化不足，建议补充性能、规模或业务结果。")
    return gaps[:4] or ["建议补充与该岗位最相关的项目难点、技术取舍和结果指标。"]


def _prep_focus(job: JobPost, skill_hits: list[str]) -> list[str]:
    focus = [f"{skill} 在项目中的落地和追问点" for skill in skill_hits[:3]]
    if job.job_family:
        focus.append(f"{job.job_family} 常见系统设计和排查题")
    for skill in (job.skills or [])[:4]:
        if skill not in skill_hits:
            focus.append(f"{skill} 基础与岗位要求对齐")
    return focus[:5] or ["围绕岗位描述准备项目复盘。"]


def _fallback_recommendations(resume_text: str) -> list[JobRecommendation]:
    lower = resume_text.lower()
    role = "后端开发实习生"
    if any(word in lower for word in ("大模型", "llm", "agent")):
        role = "AI 应用开发实习生"
    elif any(word in lower for word in ("spark", "flink", "数据")):
        role = "数据开发实习生"
    return [
        JobRecommendation(
            source="fallback",
            job_id=None,
            title=role,
            company="知识库外推荐",
            city=None,
            job_family=None,
            seniority="实习/校招",
            source_url=None,
            match_score=0,
            match_reasons=["岗位知识库未找到高匹配 JD，基于简历技能画像自由推荐。"],
            gaps=["建议先补充更明确的目标岗位和代表项目。"],
            prep_focus=["项目复盘", "核心技术栈基础", "岗位动机表达"],
            matched_keywords=[],
            evidence_chunks=[],
        )
    ]


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()
