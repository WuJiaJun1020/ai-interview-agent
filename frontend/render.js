import { state } from "./state.js?v=20260610-readme-shots-1";
import {
  $,
  escapeHtml,
  orderedDifficulties,
  questionTypeLabel,
  reportNextSteps,
  scoreLevel,
  scoreSourceLabel,
  isChoiceType,
} from "./utils.js?v=20260610-readme-shots-1";

export function updateFilterSummary(filters) {
  $("filterSummary").textContent = `${filters.category || "全部分类"} · ${filters.difficulty || "全部难度"}`;
}

export function updateInterviewConfigSummary(config) {
  const summary = [
    `简历：${config.resumeLabel || "未选择"}`,
    `岗位：${config.jobLabel || "未选择"}`,
    `题数：${config.total_questions}`,
  ].join(" · ");
  $("interviewConfigSummary").textContent = `岗位 HR 面试 · ${summary}`;
}

export function updatePracticeSummary() {
  if (!state.practiceQuestion) {
    $("practiceSummary").textContent = "未选择题目";
    $("practiceSummaryDetail").textContent = "可以从题库列表选择，或随机抽题。";
    return;
  }

  $("practiceSummary").textContent = `#${state.practiceQuestion.id} ${state.practiceQuestion.category}`;
  $("practiceSummaryDetail").textContent = `${state.practiceQuestion.difficulty} · ${state.practiceQuestion.question}`;
}

export function updateAnswerMeta(textareaId, metaId) {
  if (!$(textareaId) || !$(metaId)) return;
  const value = $(textareaId).value.trim();
  const count = value ? value.length : 0;
  $(metaId).textContent = `${count} 字`;
}

export function renderQuestionCount(questions, allQuestions) {
  $("questionCount").textContent = `题库：${questions.length} 道`;
  $("librarySummary").textContent = summarizeQuestionBank(allQuestions, questions.length);
}

export function renderFilterOptions(allQuestions) {
  const currentCategory = $("category").value;
  const currentDifficulty = $("difficulty").value;
  const categories = [...new Set(allQuestions.map((question) => question.category))].sort();
  const difficulties = orderedDifficulties([...new Set(allQuestions.map((question) => question.difficulty))]);

  $("category").innerHTML = [
    '<option value="">全部</option>',
    ...categories.map((category) => `<option value="${escapeHtml(category)}">${escapeHtml(category)}</option>`),
  ].join("");
  $("category").value = categories.includes(currentCategory) ? currentCategory : "";

  $("difficulty").innerHTML = [
    '<option value="">全部</option>',
    ...difficulties.map((difficulty) => `<option value="${escapeHtml(difficulty)}">${escapeHtml(difficulty)}</option>`),
  ].join("");
  $("difficulty").value = difficulties.includes(currentDifficulty) ? currentDifficulty : "";

  if ($("categoryOptions")) {
    $("categoryOptions").innerHTML = categories
      .map((category) => `<option value="${escapeHtml(category)}"></option>`)
      .join("");
  }
  if ($("difficultyOptions")) {
    $("difficultyOptions").innerHTML = difficulties
      .map((difficulty) => `<option value="${escapeHtml(difficulty)}"></option>`)
      .join("");
  }
}

export function renderQuestionList(questions) {
  const list = $("questionList");
  $("questionListMeta").textContent = `${questions.length} 道`;

  if (!questions.length) {
    list.classList.add("empty");
    list.innerHTML = `
      <div class="empty-state">
        <strong>当前筛选下还没有题目</strong>
        <p>可以点击“初始化题库”，或调整分类、难度筛选范围。</p>
      </div>
    `;
    return;
  }

  list.classList.remove("empty");
  list.innerHTML = questions
    .map(
      (question) => `
        <article class="question-item ${question.id === state.practiceQuestion?.id ? "selected" : ""}">
          <div>
            <div class="question-item-title">${escapeHtml(question.question)}</div>
            <div class="question-item-tags">#${question.id} · ${escapeHtml(question.category)} · ${escapeHtml(question.difficulty)} · ${questionTypeLabel(question.question_type)}</div>
          </div>
          <div class="question-item-actions">
            <button class="small-btn" type="button" data-practice-id="${question.id}">练这题</button>
          </div>
        </article>
      `,
    )
    .join("");
}

export function renderQuestion(target, question) {
  target.classList.remove("empty");
  const rubricHtml = isChoiceType(question.question_type)
    ? ""
    : `
      <div class="rubric-box">
        <strong>评分点</strong>
        ${renderPointList(question.rubric)}
      </div>
    `;
  target.innerHTML = `
    <div class="question-card-meta">
      <span>#${question.id}</span>
      <span>${escapeHtml(question.category)}</span>
      <span>${escapeHtml(question.difficulty)}</span>
      <span>${questionTypeLabel(question.question_type)}</span>
    </div>
    <p class="question-card-title">${escapeHtml(question.question)}</p>
    ${rubricHtml}
  `;
}

export function renderHrQuestion(target, question, context = null) {
  target.classList.remove("empty");
  target.innerHTML = `
    ${renderHrIntroMessage(context)}
    ${state.interviewLogs.length ? "" : renderChatMessage({
      role: "user",
      body: "<p>好的，开始吧！</p>",
    })}
    ${renderHrHistoryMessages()}
    ${renderChatMessage({
      role: "ai",
      body: `<p>${escapeHtml(question.question)}</p>`,
    })}
  `;
  scrollChatToBottom(target);
}

export function renderHrStreamText(target, title, text, context = null) {
  target.classList.remove("empty");
  target.innerHTML = `
    ${renderHrIntroMessage(context)}
    ${renderChatMessage({
      role: "user",
      body: "<p>好的，开始吧！</p>",
      time: currentTimeText(),
    })}
    ${renderChatMessage({
      role: "ai",
      body: text
        ? `<p>${escapeHtml(text)}</p>`
        : `<div class="typing-indicator" aria-label="${escapeHtml(title)}"><span></span><span></span><span></span></div>`,
      time: text ? currentTimeText() : title,
    })}
  `;
  scrollChatToBottom(target);
}

export function renderHrTurnSummary(target, turn) {
  target.classList.remove("empty");
  const endText = turn.terminationReason
    ? "我们先到这里，本轮面试结束。感谢你的参与。"
    : "本轮面试到这里结束，感谢你的参与。";
  target.innerHTML = `
    ${renderHrIntroMessage(state.hrInterviewContext)}
    ${renderHrHistoryMessages()}
    ${renderChatMessage({
      role: "ai",
      body: `<p>${escapeHtml(endText)}</p>`,
      time: currentTimeText(),
    })}
  `;
  scrollChatToBottom(target);
}

export function renderHrTurnStream(target, turn) {
  target.classList.remove("empty");
  const nextQuestionHtml = turn.nextQuestionText
    ? renderChatMessage({
        role: "ai",
        body: `<p>${escapeHtml(turn.nextQuestionText)}</p>`,
        time: currentTimeText(),
      })
    : "";
  const waitingHtml = turn.nextQuestionText || turn.isFinished
    ? ""
    : renderChatMessage({
        role: "ai",
        body: '<div class="typing-indicator" aria-label="面试官正在思考"><span></span><span></span><span></span></div>',
        time: "思考中",
      });

  target.innerHTML = `
    ${renderHrIntroMessage(turn.context)}
    ${renderHrHistoryMessages()}
    ${renderChatMessage({
      role: "ai",
      body: `<p>${escapeHtml(turn.question || "")}</p>`,
    })}
    ${renderChatMessage({
      role: "user",
      body: `<p>${escapeHtml(turn.answer || "")}</p>`,
      time: currentTimeText(),
    })}
    ${waitingHtml}
    ${nextQuestionHtml}
  `;
  scrollChatToBottom(target);
}

function renderHrIntroMessage(context = null) {
  const jobTitle = context?.job_title || "目标岗位";
  const company = context?.company || "岗位库";
  const resume = context?.resume_filename || "已选择简历";
  return renderChatMessage({
    role: "ai",
    body: `
      <p>你好，我是你的 AI 面试官。</p>
      <p>我们将开始岗位 HR 面试。本轮会围绕 ${escapeHtml(company)} · ${escapeHtml(jobTitle)}，结合 ${escapeHtml(resume)} 进行提问。</p>
      <p>请尽量结合你的经历回答，展示你的思考和能力。</p>
    `,
    time: "面试开始",
  });
}

function renderHrHistoryMessages() {
  if (!state.interviewLogs.length) return "";
  return state.interviewLogs
    .map((turn) =>
      [
        renderChatMessage({
          role: "ai",
          body: `<p>${escapeHtml(turn.question || `第 ${turn.index} 题`)}</p>`,
        }),
        renderChatMessage({
          role: "user",
          body: `<p>${escapeHtml(turn.answer || "")}</p>`,
        }),
      ].join(""),
    )
    .join("");
}

function renderChatMessage({ role, body, time = currentTimeText() }) {
  const isUser = role === "user";
  return `
    <div class="chat-message ${isUser ? "user-message" : "ai-message"}">
      ${isUser ? "" : '<div class="chat-avatar bot-avatar">AI</div>'}
      <div class="chat-message-content">
        <div class="chat-bubble">${body}</div>
        <span class="chat-time">${escapeHtml(time)}</span>
      </div>
      ${isUser ? '<div class="chat-avatar user-avatar">我</div>' : ""}
    </div>
  `;
}

function currentTimeText() {
  return new Intl.DateTimeFormat("zh-CN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date());
}

function scrollChatToBottom(target) {
  window.requestAnimationFrame(() => {
    target.scrollTop = target.scrollHeight;
  });
}

export function renderPracticeResult(result) {
  const target = $("practiceResult");
  const source = scoreSourceLabel(result.source);
  target.classList.remove("empty");
  target.innerHTML = `
    <div class="score-card">
      <div class="score">${result.score}</div>
      <div>
        <div class="score-card-header">
          <strong>本次评分</strong>
          <span class="source-badge ${source.className}">${source.label}</span>
        </div>
        <p>${escapeHtml(result.feedback)}</p>
      </div>
    </div>
    ${renderAnalysisSections(result)}
    <div class="feedback-grid">
      <div>
        <strong>已覆盖</strong>
        ${renderPointList(result.matched_rubric)}
      </div>
      <div>
        <strong>待补充</strong>
        ${renderPointList(result.missing_rubric)}
      </div>
    </div>
    <hr />
    <strong>参考答案</strong>
    <p>${escapeHtml(result.standard_answer)}</p>
  `;
}

export function renderPracticePending(message) {
  const target = $("practiceResult");
  target.classList.remove("empty");
  target.innerHTML = `
    <div class="pending-card">
      <div class="loading-dot"></div>
      <div>
        <strong>正在评分</strong>
        <p>${escapeHtml(message)}</p>
      </div>
    </div>
  `;
}

export function renderPointList(items) {
  if (!items.length) return '<p class="meta">暂无</p>';
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

export function renderAnalysisSections(result) {
  return `
    <div class="analysis-grid">
      <section>
        <strong>优点</strong>
        ${renderPointList(result.strengths || [])}
      </section>
      <section>
        <strong>问题</strong>
        ${renderPointList(result.weaknesses || [])}
      </section>
      <section>
        <strong>建议</strong>
        ${renderPointList(result.suggestions || [])}
      </section>
    </div>
  `;
}

export function updateInterviewProgress(answeredCount, totalQuestions) {
  const currentStep = Math.min(answeredCount + 1, totalQuestions || 1);
  const isFinished = answeredCount >= totalQuestions && totalQuestions > 0;
  $("interviewProgress").textContent = isFinished ? "已完成" : `第 ${currentStep}/${totalQuestions} 题`;
  const percent = totalQuestions ? Math.round((currentStep / totalQuestions) * 100) : 0;
  $("interviewProgressBar").style.width = `${percent}%`;
}

export function updateInterviewRecordsLayout() {
  const view = $("interviewView");
  const toggleButton = $("toggleInterviewRecordsBtn");
  const collapseButton = $("collapseInterviewRecordsBtn");
  if (!view || !toggleButton) return;

  view.classList.toggle("records-expanded", state.interviewRecordsExpanded);
  toggleButton.textContent = state.interviewRecordsExpanded ? "收起记录" : "展开记录";
  toggleButton.setAttribute("aria-pressed", String(state.interviewRecordsExpanded));
  if (collapseButton) collapseButton.hidden = !state.interviewRecordsExpanded;
}

export function renderInterviewLogs(report = null) {
  const target = $("interviewResult");
  target.classList.remove("empty");
  state.selectedInterviewReport = report || state.selectedInterviewReport;
  const visibleReport = report || state.selectedInterviewReport;
  const currentItems = visibleReport
    ? visibleReport.answers.map((item, index) => ({ ...item, index: index + 1 }))
    : state.interviewLogs;
  const currentAverage = visibleReport ? visibleReport.average_score : averageInterviewScore();
  const currentLevel = scoreLevel(currentAverage);
  const summaryHtml = currentItems.length
    ? `
      <section class="interview-summary-card compact-record-summary">
        <div>
          <span class="overview-label">平均分</span>
          <strong>${currentAverage} 分</strong>
        </div>
        <div>
          <span class="overview-label">已完成</span>
          <strong>${visibleReport ? `${visibleReport.answered_count}/${visibleReport.total_questions}` : `${currentItems.length} 题`}</strong>
        </div>
        <div>
          <span class="overview-label">阶段判断</span>
          <strong class="${currentLevel.className}">${currentLevel.label}</strong>
        </div>
      </section>
    `
    : "";
  const logsHtml = currentItems
    .map((item) => renderInterviewLogItem(item))
    .join("");

  const reportHtml = visibleReport ? renderFinalReport(visibleReport) : "";
  const title = visibleReport ? `面试 #${visibleReport.session_id} 记录` : "当前面试记录";
  target.innerHTML = `
    <div class="interview-record-shell">
      <section class="interview-record-main">
        <div class="record-section-heading">
          <h4>${escapeHtml(title)}</h4>
          ${visibleReport ? renderInterviewOutcome(visibleReport) : ""}
        </div>
        ${reportHtml}
        ${summaryHtml}
        <div class="interview-log">
          ${logsHtml || '<p class="meta">暂无面试记录，面试过程中会自动保存。</p>'}
        </div>
      </section>
      ${renderInterviewHistoryList(state.hrInterviewSessions)}
    </div>
  `;
}

export function renderInterviewSessions(sessions = []) {
  state.hrInterviewSessions = sessions;
  renderInterviewLogs(state.selectedInterviewReport);
}

export function renderResumeResult(payload) {
  const target = $("resumeResult");
  const analysis = payload.analysis;
  const source = scoreSourceLabel(analysis.source);
  target.classList.remove("empty");
  target.innerHTML = `
    <div class="score-card resume-headline">
      <div class="score">${payload.extracted_chars}</div>
      <div>
        <div class="score-card-header">
          <strong>${escapeHtml(payload.filename)}</strong>
          <span class="source-badge ${source.className}">${source.label}</span>
        </div>
        <p>已提取 ${payload.extracted_chars} 个字符，适合从推荐岗位和练习重点开始准备。</p>
      </div>
    </div>
    <div class="recommendation-box resume-summary-box">
      <strong>总体反馈</strong>
      <p>${escapeHtml(analysis.raw_feedback)}</p>
    </div>
    <div class="resume-grid">
      <section>
        <strong>推荐岗位</strong>
        ${renderPointList(analysis.target_roles)}
      </section>
      <section>
        <strong>识别技能</strong>
        ${renderPillList(analysis.skills)}
      </section>
      <section>
        <strong>简历亮点</strong>
        ${renderPointList(analysis.strengths)}
      </section>
      <section>
        <strong>风险与补强</strong>
        ${renderPointList(analysis.weaknesses)}
      </section>
    </div>
    ${renderResumeJobRecommendations(analysis.job_recommendations || {})}
  `;
}

function renderResumeJobRecommendations(recommendations) {
  const matched = recommendations.matched_jobs || [];
  const fallback = recommendations.fallback_recommendations || [];
  const jobs = matched.length ? matched : fallback;
  if (!jobs.length) return "";
  const sourceLabel = recommendations.knowledge_base_used ? "基于岗位知识库推荐" : "知识库不足，使用自由推荐";
  return `
    <div class="recommendation-box">
      <strong>${sourceLabel}</strong>
      <div class="resume-job-list">
        ${jobs.map(renderResumeJobRecommendation).join("")}
      </div>
    </div>
  `;
}

function renderResumeJobRecommendation(job) {
  const score = job.source === "knowledge_base" ? `${job.match_score} 分` : "自由推荐";
  const sourceLink = job.source_url
    ? `<a href="${escapeHtml(job.source_url)}" target="_blank" rel="noreferrer">来源</a>`
    : "";
  return `
    <article class="resume-job-card">
      <div class="job-item-header">
        <strong>${escapeHtml(job.title)}</strong>
        <span class="source-badge source-mock">${escapeHtml(score)}</span>
      </div>
      <p class="meta">${escapeHtml(job.company)} · ${escapeHtml(job.city || "城市不限")} · ${escapeHtml(job.job_family || "方向待确认")} · ${escapeHtml(job.seniority || "级别待确认")} ${sourceLink}</p>
      ${renderJobRankMeta(job)}
      ${renderJobFitAnalysis(job)}
      ${renderMatchedKeywords(job.matched_keywords || [])}
      ${renderEvidenceChunks(job.evidence_chunks || [])}
    </article>
  `;
}

function renderJobRankMeta(job) {
  const hasLlmRerank =
    job.llm_match_level ||
    job.llm_reasons?.length ||
    job.llm_risks?.length ||
    job.llm_resume_improvements?.length;
  if (!hasLlmRerank) return "";

  const rank = job.llm_rank ? `Top ${job.llm_rank}` : "LLM 精排";
  const level = job.llm_match_level ? ` · ${escapeHtml(job.llm_match_level)}` : "";
  const score = job.llm_match_score ? ` · ${job.llm_match_score} 分` : "";
  return `<p class="job-rank-meta">LLM 精排：${rank}${level}${score}</p>`;
}

function renderJobFitAnalysis(job) {
  const reasons = mergeTextItems(job.llm_reasons, job.match_reasons);
  const gaps = mergeTextItems(
    job.llm_risks,
    job.gaps,
    prefixItems(job.llm_resume_improvements, "简历优化："),
  );

  return `
    <div class="analysis-grid compact-analysis">
      <section>
        <strong>推荐理由</strong>
        ${renderPointList(reasons)}
      </section>
      <section>
        <strong>能力缺口</strong>
        ${renderPointList(gaps)}
      </section>
    </div>
  `;
}

function renderMatchedKeywords(keywords) {
  if (!keywords.length) return "";
  return `
    <section class="job-match-section">
      <strong>命中信号</strong>
      ${renderPillList(keywords)}
    </section>
  `;
}

function renderEvidenceChunks(chunks) {
  if (!chunks.length) return "";
  return `
    <section class="job-match-section">
      <strong>推荐依据</strong>
      <div class="evidence-list">
        ${chunks
          .map(
            (chunk) => `
              <div class="evidence-item">
                <span>${escapeHtml(chunk.chunk_type || "岗位片段")}</span>
                <p>${escapeHtml(chunk.text || "")}</p>
              </div>
            `,
          )
          .join("")}
      </div>
    </section>
  `;
}

export function renderResumePending(title, message) {
  const target = $("resumeResult");
  target.classList.remove("empty");
  target.innerHTML = `
    <div class="pending-card">
      <div class="loading-dot"></div>
      <div>
        <strong>${escapeHtml(title)}</strong>
        <p>${escapeHtml(message)}</p>
      </div>
    </div>
  `;
}

export function renderResumeError(message) {
  const target = $("resumeResult");
  target.classList.remove("empty");
  target.innerHTML = `
    <div class="error-card">
      <strong>分析失败</strong>
      <p>${escapeHtml(message)}</p>
    </div>
  `;
}

export function renderResumeHistory(items) {
  const target = $("resumeHistory");
  if (!items.length) {
    target.classList.add("empty");
    target.innerHTML = `
      <div class="empty-state">
        <strong>暂无历史记录</strong>
        <p>上传并分析一份简历后，结果会保存在这里。</p>
      </div>
    `;
    return;
  }

  target.classList.remove("empty");
  target.innerHTML = items
    .map((item) => {
      const analysis = item.latest_analysis;
      const role = analysis?.target_roles?.[0] || "未分析";
      return `
        <article class="resume-history-item">
          <div>
            <strong>${escapeHtml(item.filename)}</strong>
            <p>${escapeHtml(role)} · ${item.extracted_chars} 字</p>
          </div>
          <div class="resume-history-actions">
            <button class="small-btn secondary-btn" type="button" data-resume-id="${item.resume_id}" ${analysis ? "" : "disabled"}>查看结果</button>
            <button class="small-btn danger-btn" type="button" data-delete-resume-id="${item.resume_id}">删除</button>
          </div>
        </article>
      `;
    })
    .join("");
}

export function renderJobCollectResult(result) {
  const target = $("jobCollectResult");
  target.classList.remove("empty");
  target.innerHTML = `
    <div class="score-card">
      <div class="score">${result.created_count}</div>
      <div>
        <div class="score-card-header">
          <strong>${escapeHtml(result.filename)}</strong>
          <span class="source-badge source-mock">JSONL 导入</span>
        </div>
        <p>解析 ${result.imported_count} 条，新增 ${result.created_count} 条，跳过 ${result.skipped_count} 条，失败 ${result.failed_count} 条。</p>
      </div>
    </div>
    ${
      result.errors.length
        ? `<div class="recommendation-box"><strong>导入错误</strong>${renderPointList(result.errors)}</div>`
        : ""
    }
  `;
}

export function renderJobVectorStatus(status, pendingText = "") {
  const target = $("jobVectorStatus");
  if (!target) return;
  if (pendingText) {
    target.textContent = pendingText;
    return;
  }
  if (!status || !status.exists) {
    const reason = status?.error ? `；${status.error}` : "";
    target.textContent = `尚未构建索引，简历分析时会自动构建，也可以手动重建${reason}`;
    return;
  }
  const backendLabel = status.backend === "chroma" ? `Chroma (${status.collection_name || "job_posts"})` : "本地哈希兜底";
  const fallback = status.backend === "chroma" ? "" : "；Chroma 不可用时已自动兜底";
  target.textContent = `${backendLabel}：已索引 ${status.job_count} 个岗位 / ${status.chunk_count} 个片段，更新时间：${status.built_at || "未知"}${fallback}`;
}

export function renderJobList(jobs) {
  const target = $("jobList");
  $("jobListMeta").textContent = state.jobSearchQuery ? `${jobs.length} 条匹配` : `${jobs.length} 条`;
  if (!jobs.length) {
    target.classList.add("empty");
    target.innerHTML = `
      <div class="empty-state">
        <strong>${state.jobSearchQuery ? "没有匹配的岗位" : "暂无岗位数据"}</strong>
        <p>${state.jobSearchQuery ? "可以换一个岗位、公司、技能或 JD 关键词再试。" : "上传岗位 JSONL 文件后，导入结果会保存在这里。"}</p>
      </div>
    `;
    return;
  }

  target.classList.remove("empty");
  target.innerHTML = jobs
    .map(
      (job) => `
        <article class="job-item">
          <div class="job-item-header">
            <strong>${escapeHtml(job.title)}</strong>
            <a href="${escapeHtml(job.source_url)}" target="_blank" rel="noreferrer">来源</a>
          </div>
          <p class="meta">${escapeHtml(job.company)} · ${escapeHtml(job.city || "城市未知")} · ${escapeHtml(job.job_family || "方向待识别")} · ${escapeHtml(job.seniority || "级别待识别")}</p>
          ${renderPillList(job.skills || [])}
          ${renderJobTextSection("岗位描述", job.description)}
          ${renderJobTextSection("岗位要求", job.requirements)}
        </article>
      `,
    )
    .join("");
}

function renderJobTextSection(title, text) {
  const value = formatJobText(text);
  if (!value) return "";
  return `
    <section class="job-text-section">
      <strong>${escapeHtml(title)}</strong>
      <div class="job-text-body">${renderMultilineText(value)}</div>
    </section>
  `;
}

function formatJobText(text) {
  const value = (text || "").trim();
  if (!value) return "";
  return value
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .replace(/([。；;])\s*(团队介绍[:：])/g, "$1\n$2")
    .replace(/([。；;])\s*(工作职责[:：]|职位描述[:：]|岗位描述[:：]|岗位职责[:：]|任职要求[:：]|职位要求[:：]|岗位要求[:：])/g, "$1\n$2")
    .replace(/\s+(\d+[、.．]\s*)/g, "\n$1")
    .replace(/\n{3,}/g, "\n\n");
}

function renderMultilineText(text) {
  return escapeHtml(text).replace(/\n/g, "<br />");
}

export function renderJobPending(message) {
  const target = $("jobCollectResult");
  target.classList.remove("empty");
  target.innerHTML = `
    <div class="pending-card">
      <div class="loading-dot"></div>
      <div>
        <strong>正在导入岗位数据</strong>
        <p>${escapeHtml(message)}</p>
      </div>
    </div>
  `;
}

function summarizeQuestionBank(allQuestions, filteredCount) {
  const categories = [...new Set(allQuestions.map((question) => question.category))];
  const difficulties = orderedDifficulties([...new Set(allQuestions.map((question) => question.difficulty))]);
  const base = filteredCount ? `当前筛选下有 ${filteredCount} 道题` : "当前筛选下没有题目";
  if (!allQuestions.length) return base;
  return `${base}；全库 ${allQuestions.length} 道，覆盖 ${categories.length} 类 / ${difficulties.length} 个难度`;
}

function averageInterviewScore() {
  if (!state.interviewLogs.length) return 0;
  const total = state.interviewLogs.reduce((sum, item) => sum + item.score, 0);
  return Math.round((total / state.interviewLogs.length) * 10) / 10;
}

function renderInterviewLogItem(item) {
  const level = scoreLevel(item.score);
  const source = scoreSourceLabel(item.source);
  const focus = item.focus || [];
  return `
    <article class="interview-record-item">
      <div class="interview-record-item-header">
        <strong>第 ${item.index} 题</strong>
        <div class="interview-score-group">
          <span class="source-badge ${source.className}">${source.label}</span>
          <span class="score-badge ${level.className}">${level.label}</span>
          <span class="interview-score">${item.score} 分</span>
        </div>
      </div>
      <div class="record-qa-block">
        <span>面试官</span>
        <p>${escapeHtml(item.question || "岗位 HR 面试问题")}</p>
      </div>
      <div class="record-qa-block candidate-answer">
        <span>候选人</span>
        <p>${escapeHtml(item.answer || "")}</p>
      </div>
      ${focus.length ? `<div class="record-focus"><strong>考察重点</strong>${renderPillList(focus)}</div>` : ""}
      <details class="answer-details" open>
        <summary>面试记录与反馈</summary>
        <p>${escapeHtml(item.feedback)}</p>
        <div class="record-feedback-grid">
          <section>
            <strong>优点</strong>
            ${renderPointList(item.strengths || [])}
          </section>
          <section>
            <strong>问题</strong>
            ${renderPointList(item.weaknesses || [])}
          </section>
          <section>
            <strong>建议</strong>
            ${renderPointList(item.suggestions || [])}
          </section>
        </div>
      </details>
    </article>
  `;
}

function renderFinalReport(report) {
  const level = scoreLevel(report.average_score);
  const outcome = interviewOutcome(report);
  return `
    <article class="interview-card report-card" id="finalInterviewReport">
      <div class="interview-card-header">
        <strong>最终报告</strong>
        <div class="interview-score-group">
          <span class="score-badge ${outcome.className}">${outcome.label}</span>
          <span class="score-badge ${level.className}">${level.label}</span>
        </div>
      </div>
      <div class="report-metrics">
        <div>
          <span class="overview-label">平均分</span>
          <strong class="report-score">${report.average_score}</strong>
        </div>
        <div>
          <span class="overview-label">完成题数</span>
          <strong>${report.answered_count}/${report.total_questions}</strong>
        </div>
        <div>
          <span class="overview-label">完成状态</span>
          <strong>${report.is_finished ? "已完成" : "进行中"}</strong>
        </div>
        <div>
          <span class="overview-label">通过线</span>
          <strong>${report.pass_score} 分</strong>
        </div>
      </div>
      ${report.termination_reason ? `<div class="termination-box"><strong>提前终止</strong><p>${escapeHtml(report.termination_reason)}</p></div>` : ""}
      <div class="recommendation-box">
        <strong>复习建议</strong>
        <p>${escapeHtml(report.recommendation)}</p>
      </div>
      <div class="recommendation-box">
        <strong>下一步行动</strong>
        ${renderPointList(reportNextSteps(report.average_score))}
      </div>
    </article>
  `;
}

function renderInterviewOutcome(report) {
  if (!report || report.passed === null || report.passed === undefined) return "";
  const outcome = interviewOutcome(report);
  return `<span class="score-badge ${outcome.className}">${outcome.label}</span>`;
}

function interviewOutcome(report) {
  if (report.termination_reason) return { label: "提前终止", className: "level-weak" };
  if (report.passed === true) return { label: "面试通过，可录取", className: "level-strong" };
  if (report.passed === false) return { label: "未通过", className: "level-weak" };
  return { label: "评估中", className: "level-ok" };
}

function renderInterviewHistoryList(sessions = []) {
  const items = sessions
    .map((item) => {
      const outcome = interviewOutcome(item);
      const title = `${item.context.company} · ${item.context.job_title}`;
      return `
        <article class="interview-history-item">
          <div>
            <strong>${escapeHtml(title)}</strong>
            <p>${escapeHtml(item.context.resume_filename)} · ${item.answered_count}/${item.total_questions} 题 · ${item.average_score} 分</p>
          </div>
          <span class="score-badge ${outcome.className}">${outcome.label}</span>
          <button class="ghost-btn small-btn" type="button" data-interview-report-id="${item.session_id}">查看</button>
        </article>
      `;
    })
    .join("");
  return `
    <section class="interview-history-panel">
      <div class="record-section-heading">
        <h4>历史面试</h4>
        <span>${sessions.length} 场</span>
      </div>
      <div class="interview-history-list">
        ${items || '<p class="meta">暂无历史面试。完成面试后会保存在这里。</p>'}
      </div>
    </section>
  `;
}

function renderPillList(items) {
  if (!items.length) return '<p class="meta">暂无</p>';
  return `<div class="pill-list">${items.map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div>`;
}

function prefixItems(items = [], prefix = "") {
  return items.map((item) => `${prefix}${item}`);
}

function mergeTextItems(...groups) {
  const seen = new Set();
  const merged = [];
  groups.flat().forEach((item) => {
    const value = String(item || "").trim();
    if (!value || seen.has(value)) return;
    seen.add(value);
    merged.push(value);
  });
  return merged;
}
