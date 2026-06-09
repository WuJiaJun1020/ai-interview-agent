import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import interview, question  # noqa: F401, E402
from app.core.config import settings  # noqa: E402
from app.services import llm_scoring  # noqa: E402
from app.services import resume_analysis  # noqa: E402
from app.services import job_vector_store  # noqa: E402
from app.api import resumes as resumes_api  # noqa: E402


@pytest.fixture(autouse=True)
def force_mock_scoring(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "scoring_mode", "mock")
    monkeypatch.setattr(job_vector_store, "INDEX_PATH", tmp_path / "job_index.json")
    monkeypatch.setattr(job_vector_store, "CHROMA_PATH", tmp_path / "chroma")


@pytest.fixture()
def client(tmp_path: Path) -> TestClient:
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db: Session = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_health_config_and_frontend(client: TestClient) -> None:
    health_response = client.get("/api/health")
    assert health_response.status_code == 200
    assert health_response.json()["status"] == "ok"

    config_response = client.get("/api/config/status")
    assert config_response.status_code == 200
    config_payload = config_response.json()
    assert config_payload["scoring_mode"] in {"mock", "llm"}
    assert "openai_api_key" not in config_payload

    frontend_response = client.get("/")
    assert frontend_response.status_code == 200
    assert "AI Interview Agent" in frontend_response.text
    assert 'id="filterSummary"' in frontend_response.text
    assert 'id="practiceSummary"' in frontend_response.text
    assert 'id="interviewSummary"' in frontend_response.text
    assert 'id="interviewResult"' in frontend_response.text
    assert 'id="resumeForm"' in frontend_response.text
    assert 'id="resumeResult"' in frontend_response.text
    assert 'id="jobCollectForm"' in frontend_response.text
    assert 'id="jobList"' in frontend_response.text


def test_question_bank_crud_and_practice_flow(client: TestClient) -> None:
    seed_response = client.post("/api/questions/seed")
    assert seed_response.status_code == 200
    assert seed_response.json()["created"] > 0

    duplicate_seed_response = client.post("/api/questions/seed")
    assert duplicate_seed_response.status_code == 200
    assert duplicate_seed_response.json()["created"] == 0

    all_questions_response = client.get("/api/questions")
    assert all_questions_response.status_code == 200
    all_questions = all_questions_response.json()
    assert len(all_questions) >= 69
    assert {"初级", "中级", "高级"}.issubset({item["difficulty"] for item in all_questions})
    assert {"short_answer", "single_choice", "multiple_choice"}.issubset(
        {item["question_type"] for item in all_questions}
    )

    list_response = client.get("/api/questions", params={"category": "Python"})
    assert list_response.status_code == 200
    questions = list_response.json()
    assert questions
    assert all(item["category"] == "Python" for item in questions)

    advanced_response = client.get("/api/questions", params={"category": "Python", "difficulty": "高级"})
    assert advanced_response.status_code == 200
    advanced_questions = advanced_response.json()
    assert advanced_questions
    assert all(item["difficulty"] == "高级" for item in advanced_questions)

    create_payload = {
        "category": "测试分类",
        "difficulty": "初级",
        "question": "pytest 的主要用途是什么？",
        "standard_answer": "pytest 用于编写和运行自动化测试。",
        "rubric": ["自动化测试", "断言"],
    }
    create_response = client.post("/api/questions", json=create_payload)
    assert create_response.status_code == 201
    created = create_response.json()

    update_payload = create_payload | {"question": "pytest 通常用来解决什么问题？"}
    update_response = client.put(f"/api/questions/{created['id']}", json=update_payload)
    assert update_response.status_code == 200
    assert update_response.json()["question"] == update_payload["question"]

    practice_question_response = client.get(
        "/api/practice/question",
        params={"category": "测试分类", "difficulty": "初级"},
    )
    assert practice_question_response.status_code == 200
    practice_question = practice_question_response.json()
    assert practice_question["id"] == created["id"]

    practice_answer_response = client.post(
        "/api/practice/answer",
        json={
            "question_id": created["id"],
            "answer": "pytest 可以做自动化测试，并用断言验证代码行为。",
        },
    )
    assert practice_answer_response.status_code == 200
    practice_result = practice_answer_response.json()
    assert 0 <= practice_result["score"] <= 100
    assert practice_result["source"] == "mock"
    assert practice_result["standard_answer"]
    assert "feedback" in practice_result
    assert practice_result["strengths"]
    assert practice_result["weaknesses"]
    assert practice_result["suggestions"]

    choice_payload = {
        "category": "测试分类",
        "difficulty": "初级",
        "question_type": "single_choice",
        "question": "下面哪个选项是正确答案？",
        "standard_answer": "A 是正确答案。",
        "rubric": ["是否选择正确选项"],
        "options": ["A. 正确答案", "B. 干扰项"],
        "correct_answer": "A",
    }
    choice_create_response = client.post("/api/questions", json=choice_payload)
    assert choice_create_response.status_code == 201
    choice_question = choice_create_response.json()
    assert choice_question["question_type"] == "single_choice"
    assert choice_question["options"] == choice_payload["options"]

    choice_answer_response = client.post(
        "/api/practice/answer",
        json={"question_id": choice_question["id"], "answer": "A"},
    )
    assert choice_answer_response.status_code == 200
    choice_result = choice_answer_response.json()
    assert choice_result["score"] == 100
    assert choice_result["source"] == "mock"

    multiple_choice_payload = {
        "category": "测试分类",
        "difficulty": "中级",
        "question_type": "multiple_choice",
        "question": "哪些选项是正确答案？",
        "standard_answer": "A 和 C 是正确答案。",
        "rubric": ["是否选择全部正确选项"],
        "options": ["A. 正确答案", "B. 干扰项", "C. 也是正确答案"],
        "correct_answer": "A,C",
    }
    multiple_choice_response = client.post("/api/questions", json=multiple_choice_payload)
    assert multiple_choice_response.status_code == 201
    multiple_choice_question = multiple_choice_response.json()
    assert multiple_choice_question["question_type"] == "multiple_choice"

    multiple_choice_answer_response = client.post(
        "/api/practice/answer",
        json={"question_id": multiple_choice_question["id"], "answer": "C,A"},
    )
    assert multiple_choice_answer_response.status_code == 200
    multiple_choice_result = multiple_choice_answer_response.json()
    assert multiple_choice_result["score"] == 100

    with client.stream(
        "POST",
        "/api/practice/answer/stream",
        json={"question_id": choice_question["id"], "answer": "A"},
    ) as stream_response:
        assert stream_response.status_code == 200
        stream_text = "".join(stream_response.iter_text())
    assert "event: progress" in stream_text
    assert "event: result" in stream_text
    assert '"score": 100' in stream_text

    delete_response = client.delete(f"/api/questions/{created['id']}")
    assert delete_response.status_code == 204

    deleted_get_response = client.get(f"/api/questions/{created['id']}")
    assert deleted_get_response.status_code == 404


def test_interview_flow(client: TestClient) -> None:
    seed_response = client.post("/api/questions/seed")
    assert seed_response.status_code == 200

    start_response = client.post(
        "/api/interview/sessions",
        json={"category": "Python", "difficulty": "初级", "total_questions": 2},
    )
    assert start_response.status_code == 201
    session = start_response.json()
    assert session["session_id"] > 0
    assert session["answered_count"] == 0
    assert session["total_questions"] == 2
    assert session["is_finished"] is False

    first_answer_response = client.post(
        f"/api/interview/sessions/{session['session_id']}/answer",
        json={"answer": "我会先说明核心概念，再结合项目例子回答。"},
    )
    assert first_answer_response.status_code == 200
    first_answer = first_answer_response.json()
    assert first_answer["answered_count"] == 1
    assert first_answer["is_finished"] is False
    assert first_answer["next_question"] is not None
    assert first_answer["source"] == "mock"
    assert first_answer["strengths"]
    assert first_answer["weaknesses"]
    assert first_answer["suggestions"]

    second_answer_response = client.post(
        f"/api/interview/sessions/{session['session_id']}/answer",
        json={"answer": "补充关键点、适用场景和常见问题。"},
    )
    assert second_answer_response.status_code == 200
    second_answer = second_answer_response.json()
    assert second_answer["answered_count"] == 2
    assert second_answer["is_finished"] is True
    assert second_answer["next_question"] is None

    report_response = client.get(f"/api/interview/sessions/{session['session_id']}/report")
    assert report_response.status_code == 200
    report = report_response.json()
    assert report["answered_count"] == 2
    assert report["total_questions"] == 2
    assert 0 <= report["average_score"] <= 100
    assert report["recommendation"]


def test_resume_pdf_analysis_flow(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    job_jsonl = (
        '{"source":"test","company":"测试公司","job_id":"resume-job-1","title":"Python 后端开发实习生",'
        '"city":"深圳","job_type":"internship","category":"研发-后端",'
        '"description":"负责 FastAPI 后端接口、Redis 缓存和 MySQL 数据库优化。",'
        '"requirements":["熟悉 Python 和 FastAPI","熟悉 MySQL、Redis、Docker"],'
        '"raw_text":"岗位职责：负责 FastAPI 后端接口、Redis 缓存和 MySQL 数据库优化。任职要求：熟悉 Python、FastAPI、MySQL、Redis、Docker。",'
        '"url":"https://example.com/jobs/resume-python","collected_at":"2026-06-08T23:02:14"}\n'
    )
    job_import_response = client.post(
        "/api/jobs/import-jsonl",
        files={"file": ("resume_jobs.jsonl", job_jsonl.encode("utf-8"), "text/plain")},
    )
    assert job_import_response.status_code == 200

    def fake_extract_resume_text(_, filename: str, __: str) -> str:
        if not filename.lower().endswith((".pdf", ".docx")):
            raise ValueError("Only PDF and DOCX resumes are supported")
        return (
            "张三 Python 后端开发 简历。"
            "项目使用 FastAPI、MySQL、Redis、Docker 部署，负责接口设计、缓存优化和性能排查。"
            "项目上线后接口耗时优化 30%。"
        )

    monkeypatch.setattr(
        resumes_api,
        "extract_resume_text",
        fake_extract_resume_text,
    )

    upload_response = client.post(
        "/api/resumes/upload",
        files={"file": ("resume.pdf", b"%PDF mock", "application/pdf")},
    )
    assert upload_response.status_code == 201
    uploaded = upload_response.json()
    assert uploaded["resume_id"] > 0
    assert uploaded["filename"] == "resume.pdf"
    assert uploaded["extracted_chars"] > 20
    assert "FastAPI" in uploaded["content_preview"]

    response = client.post(f"/api/resumes/{uploaded['resume_id']}/analyze")
    assert response.status_code == 201
    payload = response.json()
    assert payload["resume_id"] == uploaded["resume_id"]
    assert payload["filename"] == "resume.pdf"
    assert payload["extracted_chars"] > 20
    analysis = payload["analysis"]
    assert analysis["source"] == "mock"
    assert "Python 后端开发实习生" in analysis["target_roles"]
    assert "Python" in analysis["skills"]
    assert "FastAPI" in analysis["skills"]
    assert "MySQL" in analysis["suggested_categories"]
    assert analysis["suggested_difficulty"] in {"初级", "中级", "高级"}
    assert analysis["interview_focus"]
    recommendations = analysis["job_recommendations"]
    assert recommendations["knowledge_base_used"] is True
    assert recommendations["matched_jobs"]
    assert recommendations["matched_jobs"][0]["source"] == "knowledge_base"
    assert recommendations["matched_jobs"][0]["title"] == "Python 后端开发实习生"
    assert recommendations["matched_jobs"][0]["matched_keywords"]
    assert recommendations["matched_jobs"][0]["evidence_chunks"]
    assert recommendations["matched_jobs"][0]["gaps"]

    history_response = client.get("/api/resumes")
    assert history_response.status_code == 200
    history = history_response.json()
    assert history
    assert history[0]["latest_analysis"]["id"] == analysis["id"]
    assert history[0]["latest_analysis"]["job_recommendations"]["matched_jobs"]

    detail_response = client.get(f"/api/resumes/{uploaded['resume_id']}")
    assert detail_response.status_code == 200
    assert detail_response.json()["analysis"]["id"] == analysis["id"]
    assert detail_response.json()["analysis"]["job_recommendations"]["matched_jobs"]

    delete_response = client.delete(f"/api/resumes/{uploaded['resume_id']}")
    assert delete_response.status_code == 204
    deleted_detail_response = client.get(f"/api/resumes/{uploaded['resume_id']}")
    assert deleted_detail_response.status_code == 404
    deleted_history_response = client.get("/api/resumes")
    assert deleted_history_response.status_code == 200
    assert all(item["resume_id"] != uploaded["resume_id"] for item in deleted_history_response.json())

    docx_response = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "resume.docx",
                b"docx mock",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert docx_response.status_code == 201
    assert docx_response.json()["filename"] == "resume.docx"

    legacy_response = client.post(
        "/api/resumes/analyze",
        files={"file": ("legacy.pdf", b"%PDF mock", "application/pdf")},
    )
    assert legacy_response.status_code == 201
    assert legacy_response.json()["analysis"]["source"] == "mock"

    invalid_response = client.post(
        "/api/resumes/upload",
        files={"file": ("resume.txt", b"text", "text/plain")},
    )
    assert invalid_response.status_code == 400


def test_job_jsonl_import_flow(client: TestClient) -> None:
    jsonl = (
        '{"source":"test","company":"测试公司","job_id":"job-1","title":"Python 后端开发工程师",'
        '"city":"深圳","job_type":"internship","category":"研发-后端",'
        '"description":"负责后端接口和服务开发。",'
        '"requirements":["熟悉 Python","熟悉 FastAPI、MySQL、Redis"],'
        '"raw_text":"岗位职责：负责后端接口。任职要求：熟悉 Python、FastAPI、MySQL、Redis。",'
        '"url":"https://example.com/jobs/python","collected_at":"2026-06-08T23:02:14"}\n'
    )

    import_response = client.post(
        "/api/jobs/import-jsonl",
        files={"file": ("jobs.jsonl", jsonl.encode("utf-8"), "text/plain")},
    )
    assert import_response.status_code == 200
    payload = import_response.json()
    assert payload["imported_count"] == 1
    assert payload["created_count"] == 1
    assert payload["updated_count"] == 0
    assert payload["skipped_count"] == 0
    assert payload["failed_count"] == 0
    assert payload["jobs"][0]["title"] == "Python 后端开发工程师"
    assert "FastAPI" in payload["jobs"][0]["skills"]

    duplicate_response = client.post(
        "/api/jobs/import-jsonl",
        files={"file": ("jobs.jsonl", jsonl.encode("utf-8"), "text/plain")},
    )
    assert duplicate_response.status_code == 200
    duplicate_payload = duplicate_response.json()
    assert duplicate_payload["created_count"] == 0
    assert duplicate_payload["updated_count"] == 1
    assert duplicate_payload["skipped_count"] == 0

    list_response = client.get("/api/jobs")
    assert list_response.status_code == 200
    jobs = list_response.json()
    assert jobs
    assert jobs[0]["company"] == "测试公司"

    search_response = client.get("/api/jobs", params={"q": "FastAPI"})
    assert search_response.status_code == 200
    search_jobs = search_response.json()
    assert search_jobs
    assert search_jobs[0]["title"] == "Python 后端开发工程师"

    status_response = client.get("/api/jobs/vector-index/status")
    assert status_response.status_code == 200

    rebuild_response = client.post("/api/jobs/vector-index/rebuild")
    assert rebuild_response.status_code == 200
    rebuild_payload = rebuild_response.json()
    assert rebuild_payload["exists"] is True
    assert rebuild_payload["backend"] == "chroma"
    assert rebuild_payload["collection_name"] == "job_posts"
    assert rebuild_payload["chroma_available"] is True
    assert rebuild_payload["job_count"] == 1
    assert rebuild_payload["chunk_count"] >= 1

    invalid_response = client.post(
        "/api/jobs/import-jsonl",
        files={"file": ("jobs.json", b"{}", "application/json")},
    )
    assert invalid_response.status_code == 400


def test_qwen_compatible_llm_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeMessage:
        content = (
            '{"score": 88, "feedback": "回答结构清晰。", '
            '"matched_rubric": ["核心概念"], "missing_rubric": ["项目例子"], '
            '"strengths": ["概念准确"], "weaknesses": ["缺少项目例子"], "suggestions": ["补充实践场景"]}'
        )

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, api_key: str, base_url: str, timeout: float):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            captured["timeout"] = timeout
            self.chat = FakeChat()

    monkeypatch.setattr(llm_scoring, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "dashscope_api_key", "test-dashscope-key")
    monkeypatch.setattr(settings, "openai_base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setattr(settings, "openai_model", "qwen3.7-plus")
    monkeypatch.setattr(settings, "llm_enable_thinking", True)

    result = llm_scoring.score_answer_with_llm(
        question="什么是索引？",
        answer="索引用于加速查询。",
        standard_answer="索引帮助数据库减少扫描范围。",
        rubric=["核心概念", "项目例子"],
    )

    assert result.score == 88
    assert result.source == "llm"
    assert result.strengths == ["概念准确"]
    assert result.weaknesses == ["缺少项目例子"]
    assert result.suggestions == ["补充实践场景"]
    assert captured["api_key"] == "test-dashscope-key"
    assert captured["base_url"] == "https://dashscope.aliyuncs.com/compatible-mode/v1"
    assert captured["timeout"] == settings.llm_timeout_seconds
    assert captured["model"] == "qwen3.7-plus"
    assert captured["extra_body"] == {"enable_thinking": True}


def test_resume_llm_analysis_uses_top_8_and_returns_top_3_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class FakeMessage:
        content = (
            '{"target_roles": ["Python 后端开发工程师"], '
            '"skills": ["Python", "FastAPI", "Redis"], '
            '"strengths": ["项目经验贴近后端岗位"], '
            '"weaknesses": ["缺少量化指标"], '
            '"suggested_categories": ["Python", "FastAPI", "Redis"], '
            '"suggested_difficulty": "中级", '
            '"interview_focus": ["FastAPI 项目追问", "Redis 缓存设计"], '
            '"raw_feedback": "已结合 Top 8 JD 完成岗位定位。", '
            '"ranked_jobs": ['
            '{"job_id": 3, "rank": 1, "match_level": "强匹配", "match_score": 92, '
            '"reasons": ["项目经验最贴近"], "risks": ["需要补充指标"], "resume_improvements": ["突出 FastAPI 项目"]},'
            '{"job_id": 1, "rank": 2, "match_level": "可冲刺", "match_score": 84, '
            '"reasons": ["技能覆盖较好"], "risks": [], "resume_improvements": ["补充 Redis 细节"]},'
            '{"job_id": 2, "rank": 3, "match_level": "可冲刺", "match_score": 78, '
            '"reasons": ["方向相关"], "risks": ["岗位要求偏高"], "resume_improvements": []}'
            ']}'
        )

    class FakeChoice:
        message = FakeMessage()

    class FakeResponse:
        choices = [FakeChoice()]

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            payload = json.loads(kwargs["messages"][1]["content"])
            candidates = payload["job_knowledge_context"]["matched_jobs"]
            captured["candidate_count"] = len(candidates)
            captured["candidate_ids"] = [item["job_id"] for item in candidates]
            return FakeResponse()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, api_key: str, base_url: str, timeout: float):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            captured["timeout"] = timeout
            self.chat = FakeChat()

    monkeypatch.setattr(resume_analysis, "OpenAI", FakeOpenAI)
    monkeypatch.setattr(settings, "scoring_mode", "llm")
    monkeypatch.setattr(settings, "openai_api_key", "test-openai-key")
    monkeypatch.setattr(settings, "dashscope_api_key", "")
    monkeypatch.setattr(settings, "openai_base_url", "https://example.test/v1")
    monkeypatch.setattr(settings, "openai_model", "test-model")
    monkeypatch.setattr(settings, "llm_enable_thinking", False)

    jobs = [
        {
            "source": "knowledge_base",
            "job_id": index,
            "title": f"岗位 {index}",
            "company": "测试公司",
            "city": "深圳",
            "job_family": "后端",
            "seniority": "校招",
            "source_url": "https://example.com",
            "match_score": 60 + index,
            "match_reasons": ["规则原因"],
            "gaps": ["能力缺口"],
            "prep_focus": ["准备重点"],
            "matched_keywords": ["Python", "FastAPI"],
            "evidence_chunks": [{"chunk_type": "岗位要求", "text": "熟悉 Python 和 FastAPI"}],
        }
        for index in range(1, 10)
    ]
    context = {"knowledge_base_used": True, "matched_jobs": jobs, "fallback_recommendations": []}

    result = resume_analysis.analyze_resume_text("Python FastAPI Redis 项目经验", context)

    assert captured["candidate_count"] == 8
    assert captured["candidate_ids"] == list(range(1, 9))
    assert captured["timeout"] == settings.llm_timeout_seconds
    assert result.source == "llm"
    assert result.target_roles == ["Python 后端开发工程师"]
    assert context["rerank"]["source"] == "llm_analysis"
    assert context["rerank"]["mode"] == "single_call"
    assert context["rerank"]["candidate_count"] == 8
    assert [job["job_id"] for job in context["matched_jobs"]] == [3, 1, 2]
    assert context["matched_jobs"][0]["llm_match_level"] == "强匹配"
    assert context["matched_jobs"][0]["match_score"] == 92
