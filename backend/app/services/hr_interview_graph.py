from dataclasses import dataclass
from typing import Any, TypedDict

from app.models.job import JobPost
from app.models.resume import Resume

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:  # LangGraph is optional at runtime until dependencies are installed.
    END = None
    START = None
    StateGraph = None


class HrInterviewGraphState(TypedDict, total=False):
    mode: str
    resume_text: str
    job: dict[str, Any]
    previous_turns: list[dict[str, Any]]
    question_index: int
    total_questions: int
    current_question: str
    answer: str
    job_skills: list[str]
    resume_skill_hits: list[str]
    missing_skills: list[str]
    covered_focus: list[str]
    answer_signals: dict[str, bool]
    risk_flags: list[str]
    stage: str
    decision: str
    primary_focus: str
    focus: list[str]
    intent: str
    guidance: str
    question_seed: str
    graph_backend: str


@dataclass(frozen=True)
class HrInterviewStrategy:
    stage: str
    decision: str
    primary_focus: str
    focus: list[str]
    intent: str
    guidance: str
    question_seed: str
    covered_focus: list[str]
    risk_flags: list[str]
    backend: str


_COMPILED_GRAPH: Any | None = None


def plan_hr_question_strategy(
    resume: Resume,
    job: JobPost,
    previous_turns: list[dict[str, Any]],
    question_index: int,
    total_questions: int,
) -> HrInterviewStrategy:
    state = _run_strategy_graph(
        {
            "mode": "question",
            "resume_text": resume.content or "",
            "job": _job_payload(job),
            "previous_turns": previous_turns,
            "question_index": question_index,
            "total_questions": total_questions,
        }
    )
    return _strategy_from_state(state)


def plan_hr_review_strategy(
    resume: Resume,
    job: JobPost,
    question: str,
    answer: str,
    previous_turns: list[dict[str, Any]],
) -> HrInterviewStrategy:
    state = _run_strategy_graph(
        {
            "mode": "review",
            "resume_text": resume.content or "",
            "job": _job_payload(job),
            "previous_turns": previous_turns,
            "current_question": question,
            "answer": answer,
            "question_index": len(previous_turns) + 1,
            "total_questions": max(len(previous_turns) + 1, 1),
        }
    )
    return _strategy_from_state(state)


def strategy_payload(strategy: HrInterviewStrategy) -> dict[str, Any]:
    return {
        "stage": strategy.stage,
        "decision": strategy.decision,
        "primary_focus": strategy.primary_focus,
        "focus": strategy.focus,
        "intent": strategy.intent,
        "guidance": strategy.guidance,
        "covered_focus": strategy.covered_focus,
        "risk_flags": strategy.risk_flags,
        "graph_backend": strategy.backend,
    }


def _run_strategy_graph(initial_state: HrInterviewGraphState) -> HrInterviewGraphState:
    if StateGraph is None:
        state = _run_strategy_steps(initial_state)
        state["graph_backend"] = "fallback"
        return state

    try:
        graph = _compiled_graph()
        state = graph.invoke(initial_state)
        state["graph_backend"] = "langgraph"
        return state
    except Exception:
        state = _run_strategy_steps(initial_state)
        state["graph_backend"] = "fallback"
        return state


def _compiled_graph() -> Any:
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is not None:
        return _COMPILED_GRAPH
    builder = StateGraph(HrInterviewGraphState)
    builder.add_node("collect_signals", _collect_signals)
    builder.add_node("choose_stage", _choose_stage)
    builder.add_node("compose_strategy", _compose_strategy)
    builder.add_edge(START, "collect_signals")
    builder.add_edge("collect_signals", "choose_stage")
    builder.add_edge("choose_stage", "compose_strategy")
    builder.add_edge("compose_strategy", END)
    _COMPILED_GRAPH = builder.compile()
    return _COMPILED_GRAPH


def _run_strategy_steps(initial_state: HrInterviewGraphState) -> HrInterviewGraphState:
    state: HrInterviewGraphState = dict(initial_state)
    for step in (_collect_signals, _choose_stage, _compose_strategy):
        state.update(step(state))
    return state


def _collect_signals(state: HrInterviewGraphState) -> HrInterviewGraphState:
    job = state.get("job", {})
    resume_text = state.get("resume_text", "")
    previous_turns = state.get("previous_turns", [])
    skills = _job_skills(job)
    resume_lower = resume_text.lower()
    resume_hits = [skill for skill in skills if skill.lower() in resume_lower]
    covered_focus = _covered_focus(previous_turns, skills)
    missing_skills = [skill for skill in skills if skill not in resume_hits and skill not in covered_focus]

    answer = state.get("answer") or _last_turn_answer(previous_turns)
    answer_signals = _answer_signals(answer)
    risk_flags = _risk_flags(answer_signals)
    last_score = _last_turn_score(previous_turns)
    if last_score is not None and last_score < 60:
        risk_flags.append("上一轮得分偏低")

    return {
        "job_skills": skills,
        "resume_skill_hits": resume_hits,
        "missing_skills": missing_skills,
        "covered_focus": covered_focus,
        "answer_signals": answer_signals,
        "risk_flags": risk_flags,
    }


def _choose_stage(state: HrInterviewGraphState) -> HrInterviewGraphState:
    mode = state.get("mode", "question")
    question_index = int(state.get("question_index") or 1)
    total_questions = max(int(state.get("total_questions") or 1), 1)
    risk_flags = state.get("risk_flags", [])
    missing_skills = state.get("missing_skills", [])

    if mode == "question" and question_index > 1 and _needs_follow_up(risk_flags):
        return {"stage": "evidence_follow_up", "decision": "follow_up"}
    if mode == "review":
        return {"stage": "answer_review", "decision": "review"}
    if question_index == 1:
        return {"stage": "opening_alignment", "decision": "new_question"}
    if question_index >= total_questions:
        return {"stage": "closing_summary", "decision": "finish_after_answer"}
    if missing_skills and question_index >= max(2, total_questions - 1):
        return {"stage": "gap_probe", "decision": "new_question"}
    if question_index % 3 == 0:
        return {"stage": "problem_solving", "decision": "new_question"}
    return {"stage": "project_evidence", "decision": "new_question"}


def _compose_strategy(state: HrInterviewGraphState) -> HrInterviewGraphState:
    job = state.get("job", {})
    skills = state.get("job_skills", [])
    resume_hits = state.get("resume_skill_hits", [])
    missing_skills = state.get("missing_skills", [])
    stage = state.get("stage", "project_evidence")
    primary_focus = _primary_focus(stage, skills, resume_hits, missing_skills)
    focus = _focus_items(stage, primary_focus, skills, missing_skills, state.get("risk_flags", []))
    intent = _intent(stage, job, primary_focus)
    guidance = _guidance(stage, primary_focus)
    question_seed = _question_seed(stage, job, primary_focus)
    return {
        "primary_focus": primary_focus,
        "focus": focus,
        "intent": intent,
        "guidance": guidance,
        "question_seed": question_seed,
    }


def _strategy_from_state(state: HrInterviewGraphState) -> HrInterviewStrategy:
    return HrInterviewStrategy(
        stage=state.get("stage") or "project_evidence",
        decision=state.get("decision") or "new_question",
        primary_focus=state.get("primary_focus") or "项目经验",
        focus=_as_string_list(state.get("focus")) or ["岗位匹配", "项目证据"],
        intent=state.get("intent") or "围绕目标岗位继续追问候选人的真实项目经验。",
        guidance=state.get("guidance") or "回答需要补充具体项目、个人动作和结果。",
        question_seed=state.get("question_seed") or "",
        covered_focus=_as_string_list(state.get("covered_focus")),
        risk_flags=_as_string_list(state.get("risk_flags")),
        backend=state.get("graph_backend") or "fallback",
    )


def _job_payload(job: JobPost) -> dict[str, Any]:
    return {
        "title": job.title,
        "company": job.company,
        "city": job.city,
        "job_family": job.job_family,
        "seniority": job.seniority,
        "skills": job.skills or [],
        "description": job.description or "",
        "requirements": job.requirements or "",
    }


def _job_skills(job: dict[str, Any]) -> list[str]:
    skills = [str(skill).strip() for skill in (job.get("skills") or []) if str(skill).strip()]
    if skills:
        return skills[:8]
    text = f"{job.get('title', '')} {job.get('description', '')} {job.get('requirements', '')}".lower()
    candidates = ["Python", "FastAPI", "MySQL", "Redis", "Docker", "Linux", "Git", "HTTP", "算法", "系统设计"]
    return [skill for skill in candidates if skill.lower() in text] or ["项目经验"]


def _covered_focus(previous_turns: list[dict[str, Any]], skills: list[str]) -> list[str]:
    text = " ".join(
        f"{turn.get('question', '')} {turn.get('answer', '')} {turn.get('feedback', '')}"
        for turn in previous_turns
    ).lower()
    covered = [skill for skill in skills if skill.lower() in text]
    generic_focus = []
    if any(keyword in text for keyword in ("why", "为什么", "投递", "动机", "匹配")):
        generic_focus.append("岗位动机")
    if any(keyword in text for keyword in ("项目", "负责", "实现", "project")):
        generic_focus.append("项目证据")
    if any(keyword in text for keyword in ("排查", "优化", "问题", "tradeoff", "取舍")):
        generic_focus.append("问题解决")
    return _dedupe([*generic_focus, *covered])


def _last_turn_answer(previous_turns: list[dict[str, Any]]) -> str:
    if not previous_turns:
        return ""
    return str(previous_turns[-1].get("answer") or "")


def _last_turn_score(previous_turns: list[dict[str, Any]]) -> int | None:
    if not previous_turns:
        return None
    try:
        return int(previous_turns[-1].get("score"))
    except (TypeError, ValueError):
        return None


def _answer_signals(answer: str) -> dict[str, bool]:
    stripped = answer.strip()
    return {
        "too_short": len(stripped) < 80,
        "has_project": _contains_any(stripped, ["项目", "负责", "实现", "上线", "project", "built", "developed"]),
        "has_action": _contains_any(stripped, ["设计", "实现", "优化", "排查", "协作", "负责", "built", "optimized"]),
        "has_result": _contains_any(stripped, ["提升", "降低", "减少", "完成", "结果", "上线", "reduced", "improved"]),
        "has_metric": any(char.isdigit() for char in stripped),
    }


def _risk_flags(answer_signals: dict[str, bool]) -> list[str]:
    flags = []
    if answer_signals.get("too_short"):
        flags.append("回答偏短")
    if not answer_signals.get("has_project"):
        flags.append("缺少项目场景")
    if not answer_signals.get("has_action"):
        flags.append("缺少个人动作")
    if not answer_signals.get("has_result") and not answer_signals.get("has_metric"):
        flags.append("缺少结果指标")
    return flags


def _needs_follow_up(risk_flags: list[str]) -> bool:
    return bool({"回答偏短", "缺少项目场景", "缺少结果指标"} & set(risk_flags))


def _primary_focus(stage: str, skills: list[str], resume_hits: list[str], missing_skills: list[str]) -> str:
    if stage == "gap_probe" and missing_skills:
        return missing_skills[0]
    if stage in {"project_evidence", "problem_solving"}:
        return (resume_hits or skills or ["项目经验"])[0]
    if stage == "evidence_follow_up":
        return (resume_hits or skills or ["项目证据"])[0]
    if stage == "closing_summary":
        return "短期贡献"
    return "岗位匹配"


def _focus_items(
    stage: str,
    primary_focus: str,
    skills: list[str],
    missing_skills: list[str],
    risk_flags: list[str],
) -> list[str]:
    stage_focus = {
        "opening_alignment": ["岗位动机", "简历匹配", primary_focus],
        "project_evidence": ["项目证据", "个人职责", primary_focus],
        "evidence_follow_up": ["追问补证", "项目细节", "量化结果", primary_focus],
        "problem_solving": ["问题解决", "判断过程", "技术取舍", primary_focus],
        "gap_probe": ["能力缺口", "学习计划", missing_skills[0] if missing_skills else primary_focus],
        "closing_summary": ["岗位胜任力", "短期贡献", "风险补充"],
        "answer_review": ["回答结构", "岗位贴合", "证据完整度", primary_focus],
    }
    focus = stage_focus.get(stage, ["项目证据", primary_focus])
    if "缺少结果指标" in risk_flags:
        focus.append("量化结果")
    if "缺少项目场景" in risk_flags:
        focus.append("真实项目")
    return _dedupe([item for item in focus if item])


def _intent(stage: str, job: dict[str, Any], primary_focus: str) -> str:
    title = job.get("title") or "目标岗位"
    company = job.get("company") or "目标公司"
    intent_map = {
        "opening_alignment": f"确认候选人投递 {company} 的 {title} 的动机，以及简历中最能证明匹配度的经历。",
        "project_evidence": f"围绕 {primary_focus} 深挖真实项目证据，判断候选人是否真的做过并能讲清职责和结果。",
        "evidence_follow_up": "上一轮回答证据不足，本轮需要追问具体项目、个人动作和量化结果。",
        "problem_solving": f"考察候选人在 {primary_focus} 相关场景下的问题定位、取舍和复盘能力。",
        "gap_probe": f"针对 JD 中的 {primary_focus} 缺口，判断候选人的补齐计划和迁移学习能力。",
        "closing_summary": f"收束本轮面试，判断候选人对 {title} 的胜任力、短期贡献和主要风险。",
        "answer_review": "根据岗位 JD、简历证据和回答完整度给出本轮反馈，并决定后续追问方向。",
    }
    return intent_map.get(stage, f"继续围绕 {title} 追问岗位匹配证据。")


def _guidance(stage: str, primary_focus: str) -> str:
    guidance_map = {
        "opening_alignment": "问题应自然开场，但必须要求候选人把岗位要求和简历经历连接起来。",
        "project_evidence": "问题只聚焦一个项目场景，要求说清背景、个人负责部分、技术动作和结果。",
        "evidence_follow_up": "问题要明显承接上一轮，要求候选人补充真实项目细节、量化指标和个人贡献。",
        "problem_solving": "问题要让候选人复盘判断过程，不只描述最终方案。",
        "gap_probe": f"问题要围绕 {primary_focus} 的能力缺口，关注学习路径、替代经验和入职后的补齐计划。",
        "closing_summary": "问题要促使候选人总结胜任理由、短期贡献和仍需补足的风险。",
        "answer_review": "反馈需要指出回答里的岗位命中点、证据缺口和下一轮最值得追问的方向。",
    }
    return guidance_map.get(stage, "问题需要具体、自然、可回答。")


def _question_seed(stage: str, job: dict[str, Any], primary_focus: str) -> str:
    title = job.get("title") or "目标岗位"
    company = job.get("company") or "目标公司"
    seed_map = {
        "opening_alignment": f"你为什么想投递 {company} 的 {title}？请结合简历里最相关的一段经历说明匹配点。",
        "project_evidence": f"请讲一个你在项目中实际使用 {primary_focus} 的场景，重点说清你负责什么、怎么做、结果如何。",
        "evidence_follow_up": "我想追问刚才的回答。请你补充一个具体项目例子，说明你的个人动作和最终结果，最好带上数据。",
        "problem_solving": f"请复盘一次和 {primary_focus} 相关的技术难点或排查问题，重点说判断过程和取舍。",
        "gap_probe": f"JD 中提到 {primary_focus}，但简历体现不多。你会如何补足，并在入职初期证明自己能胜任？",
        "closing_summary": f"最后请总结为什么你适合 {title}，以及入职后最能立刻贡献价值的地方。",
    }
    return seed_map.get(stage, f"请结合 {title} 的岗位要求，补充一个最能证明你能力的项目例子。")


def _contains_any(text: str, keywords: list[str]) -> bool:
    lower_text = text.lower()
    return any(keyword.lower() in lower_text for keyword in keywords)


def _dedupe(items: list[str]) -> list[str]:
    result = []
    seen = set()
    for item in items:
        value = str(item).strip()
        if value and value not in seen:
            result.append(value)
            seen.add(value)
    return result


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
