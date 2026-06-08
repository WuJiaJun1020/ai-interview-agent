let practiceQuestion = null;
let interviewSessionId = null;
let interviewFinished = false;
let busyCount = 0;
let questionCache = [];
let editingQuestionId = null;
let interviewLogs = [];

const $ = (id) => document.getElementById(id);

function selectedFilters() {
  return {
    category: $("category").value,
    difficulty: $("difficulty").value,
  };
}

function selectedInterviewConfig() {
  return {
    ...selectedFilters(),
    total_questions: Number($("interviewQuestionCount").value),
  };
}

function updateInterviewConfigSummary() {
  const config = selectedInterviewConfig();
  const summary = [
    `分类：${config.category || "全部"}`,
    `难度：${config.difficulty || "全部"}`,
    `题数：${config.total_questions}`,
  ].join(" · ");
  $("interviewConfigSummary").textContent = summary;
  $("interviewSummaryDetail").textContent = summary;
}

function updateFilterSummary() {
  const filters = selectedFilters();
  $("filterSummary").textContent = `${filters.category || "全部分类"} · ${filters.difficulty || "全部难度"}`;
}

function updatePracticeSummary() {
  if (!practiceQuestion) {
    $("practiceSummary").textContent = "未选择题目";
    $("practiceSummaryDetail").textContent = "可以从题库列表选择，或随机抽题。";
    return;
  }

  $("practiceSummary").textContent = `#${practiceQuestion.id} ${practiceQuestion.category}`;
  $("practiceSummaryDetail").textContent = `${practiceQuestion.difficulty} · ${practiceQuestion.question}`;
}

function updateAnswerMeta(textareaId, metaId) {
  const value = $(textareaId).value.trim();
  const count = value ? value.length : 0;
  $(metaId).textContent = `${count} 字`;
}

function syncCreateFormDefaults() {
  if ($("category").value && !$("newCategory").value) $("newCategory").value = $("category").value;
  if ($("difficulty").value && !$("newDifficulty").value) $("newDifficulty").value = $("difficulty").value;
}

function queryString(filters) {
  const params = new URLSearchParams();
  if (filters.category) params.set("category", filters.category);
  if (filters.difficulty) params.set("difficulty", filters.difficulty);
  return params.toString();
}

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

function setStatus(text) {
  $("statusText").textContent = text;
}

async function refreshConfigStatus() {
  const config = await request("/api/config/status");
  const target = $("scoringMode");
  target.classList.remove("muted-pill", "warning-pill", "success-pill");

  if (config.scoring_mode === "llm" && config.openai_configured) {
    target.classList.add("success-pill");
    target.textContent = `评分：LLM (${config.openai_model})`;
    return;
  }
  if (config.scoring_mode === "llm" && !config.openai_configured) {
    target.classList.add("warning-pill");
    target.textContent = "评分：LLM 未配置 Key";
    return;
  }

  target.classList.add("muted-pill");
  target.textContent = "评分：mock";
}

function setBusy(isBusy) {
  busyCount += isBusy ? 1 : -1;
  busyCount = Math.max(busyCount, 0);
  document.querySelectorAll("button").forEach((button) => {
    button.disabled = busyCount > 0;
  });
}

async function runAction(action, busyText) {
  setBusy(true);
  if (busyText) setStatus(busyText);
  try {
    await action();
  } catch (error) {
    setStatus(parseError(error.message));
  } finally {
    setBusy(false);
  }
}

function parseError(message) {
  if (message.includes("No question found")) return "没有找到符合条件的题目，请先初始化题库或调整筛选条件";
  if (message.includes("Interview session is finished")) return "本轮面试已结束，请开始新的面试";
  if (message.includes("Failed to fetch")) return "无法连接后端，请确认服务已启动";
  return message;
}

async function refreshQuestionCount() {
  const qs = queryString(selectedFilters());
  const questions = await request(`/api/questions${qs ? `?${qs}` : ""}`);
  questionCache = questions;
  $("questionCount").textContent = `题库：${questions.length} 道`;
  $("librarySummary").textContent = questions.length ? `当前筛选下有 ${questions.length} 道题` : "当前筛选下没有题目";
  updateFilterSummary();
  renderQuestionList(questions);
  await refreshFilterOptions();
  updateFilterSummary();
}

function orderedDifficulties(difficulties) {
  const order = ["初级", "中级", "高级"];
  return difficulties.sort((a, b) => {
    const aIndex = order.indexOf(a);
    const bIndex = order.indexOf(b);
    if (aIndex !== -1 || bIndex !== -1) {
      return (aIndex === -1 ? 99 : aIndex) - (bIndex === -1 ? 99 : bIndex);
    }
    return a.localeCompare(b, "zh-CN");
  });
}

function summarizeQuestionBank(allQuestions, filteredCount) {
  const categories = [...new Set(allQuestions.map((question) => question.category))];
  const difficulties = orderedDifficulties([...new Set(allQuestions.map((question) => question.difficulty))]);
  const base = filteredCount ? `当前筛选下有 ${filteredCount} 道题` : "当前筛选下没有题目";
  if (!allQuestions.length) return base;
  return `${base}；全库 ${allQuestions.length} 道，覆盖 ${categories.length} 类 / ${difficulties.length} 个难度`;
}

async function refreshFilterOptions() {
  const currentCategory = $("category").value;
  const currentDifficulty = $("difficulty").value;
  const allQuestions = await request("/api/questions");
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

  $("categoryOptions").innerHTML = categories
    .map((category) => `<option value="${escapeHtml(category)}"></option>`)
    .join("");
  $("difficultyOptions").innerHTML = difficulties
    .map((difficulty) => `<option value="${escapeHtml(difficulty)}"></option>`)
    .join("");
  $("librarySummary").textContent = summarizeQuestionBank(allQuestions, questionCache.length);
}

function renderQuestionList(questions) {
  const list = $("questionList");
  $("questionListMeta").textContent = `${questions.length} 道`;

  if (!questions.length) {
    list.classList.add("empty");
    list.innerHTML = `
      <div class="empty-state">
        <strong>当前筛选下还没有题目</strong>
        <p>可以点击“初始化题库”，或在下方新增一道符合这个分类和难度的题目。</p>
      </div>
    `;
    return;
  }

  list.classList.remove("empty");
  list.innerHTML = questions
    .map(
      (question) => `
        <article class="question-item ${question.id === practiceQuestion?.id ? "selected" : ""} ${question.id === editingQuestionId ? "editing" : ""}">
          <div>
            <div class="question-item-title">${escapeHtml(question.question)}</div>
            <div class="question-item-tags">#${question.id} · ${escapeHtml(question.category)} · ${escapeHtml(question.difficulty)}</div>
          </div>
          <div class="question-item-actions">
            <button class="small-btn" type="button" data-practice-id="${question.id}">练这题</button>
            <button class="small-btn secondary-btn" type="button" data-edit-id="${question.id}">编辑</button>
            <button class="small-btn danger-btn" type="button" data-delete-id="${question.id}">删除</button>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderQuestion(target, question) {
  target.classList.remove("empty");
  target.innerHTML = `
    <div class="question-card-meta">
      <span>#${question.id}</span>
      <span>${escapeHtml(question.category)}</span>
      <span>${escapeHtml(question.difficulty)}</span>
    </div>
    <p class="question-card-title">${escapeHtml(question.question)}</p>
    <div class="rubric-box">
      <strong>评分点</strong>
      ${renderPointList(question.rubric)}
    </div>
  `;
}

function renderPracticeResult(result) {
  const target = $("practiceResult");
  target.classList.remove("empty");
  target.innerHTML = `
    <div class="score-card">
      <div class="score">${result.score}</div>
      <div>
        <strong>本次评分</strong>
        <p>${escapeHtml(result.feedback)}</p>
      </div>
    </div>
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

function renderPointList(items) {
  if (!items.length) return '<p class="meta">暂无</p>';
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function scoreLevel(score) {
  if (score >= 80) return { label: "表现较好", className: "level-strong" };
  if (score >= 60) return { label: "基本达标", className: "level-ok" };
  return { label: "需要加强", className: "level-weak" };
}

function averageInterviewScore() {
  if (!interviewLogs.length) return 0;
  const total = interviewLogs.reduce((sum, item) => sum + item.score, 0);
  return Math.round((total / interviewLogs.length) * 10) / 10;
}

function reportNextSteps(averageScore) {
  if (averageScore >= 80) {
    return ["尝试提高难度或增加题数", "回答时补充更多项目细节", "练习更强的结构化表达"];
  }
  if (averageScore >= 60) {
    return ["复盘待补充概念", "每题先用 3 点结构作答", "用项目例子支撑结论"];
  }
  return ["先复习当前分类基础概念", "参考答案后重新组织回答", "减少一次性选择过多题数"];
}

function updateInterviewProgress(answeredCount, totalQuestions) {
  $("interviewProgress").textContent = `${answeredCount}/${totalQuestions}`;
  const percent = totalQuestions ? Math.round((answeredCount / totalQuestions) * 100) : 0;
  $("interviewProgressBar").style.width = `${percent}%`;
  $("interviewSummary").textContent =
    answeredCount >= totalQuestions && totalQuestions > 0 ? "已完成" : `进行中：${answeredCount}/${totalQuestions}`;
}

function renderInterviewLogs(report = null) {
  const target = $("interviewResult");
  target.classList.remove("empty");
  const currentAverage = report ? report.average_score : averageInterviewScore();
  const currentLevel = scoreLevel(currentAverage);
  const summaryHtml = interviewLogs.length
    ? `
      <section class="interview-summary-card">
        <div>
          <span class="overview-label">当前平均分</span>
          <strong>${currentAverage} 分</strong>
        </div>
        <div>
          <span class="overview-label">已完成</span>
          <strong>${interviewLogs.length} 题</strong>
        </div>
        <div>
          <span class="overview-label">阶段判断</span>
          <strong class="${currentLevel.className}">${currentLevel.label}</strong>
        </div>
      </section>
    `
    : "";
  const logsHtml = interviewLogs
    .map(
      (item) => {
        const level = scoreLevel(item.score);
        return `
        <article class="interview-card">
          <div class="interview-card-header">
            <strong>第 ${item.index} 题</strong>
            <div class="interview-score-group">
              <span class="score-badge ${level.className}">${level.label}</span>
              <span class="interview-score">${item.score} 分</span>
            </div>
          </div>
          <p class="meta">你的回答：${escapeHtml(item.answer)}</p>
          <p>${escapeHtml(item.feedback)}</p>
          <details class="answer-details">
            <summary>查看参考答案</summary>
            <p>${escapeHtml(item.standardAnswer)}</p>
          </details>
        </article>
      `;
      },
    )
    .join("");

  const reportHtml = report
    ? (() => {
        const level = scoreLevel(report.average_score);
        return `
      <article class="interview-card report-card" id="finalInterviewReport">
        <div class="interview-card-header">
          <strong>最终报告</strong>
          <span class="score-badge ${level.className}">${level.label}</span>
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
        </div>
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
      })()
    : "";

  target.innerHTML = `<div class="interview-log">${summaryHtml}${logsHtml || '<p class="meta">还没有提交回答。</p>'}${reportHtml}</div>`;
}

function useQuestionForPractice(question) {
  practiceQuestion = question;
  renderQuestion($("practiceQuestion"), practiceQuestion);
  $("practiceAnswer").value = "";
  updateAnswerMeta("practiceAnswer", "practiceAnswerMeta");
  $("practiceResult").classList.add("empty");
  $("practiceResult").textContent = "提交答案后显示评分、反馈和参考答案。";
  $("practiceMeta").textContent = `题目 #${practiceQuestion.id}`;
  updatePracticeSummary();
  setStatus("已选择题库中的题目");
  renderQuestionList(questionCache);
}

function fillQuestionForm(question) {
  editingQuestionId = question.id;
  $("newCategory").value = question.category;
  $("newDifficulty").value = question.difficulty;
  $("newQuestion").value = question.question;
  $("newStandardAnswer").value = question.standard_answer;
  $("newRubric").value = question.rubric.join("\n");
  $("questionFormTitle").textContent = `编辑题目 #${question.id}`;
  $("questionFormMeta").textContent = "保存后会更新题库列表";
  $("createQuestionBtn").textContent = "保存修改";
  $("cancelEditBtn").hidden = false;
  setStatus(`正在编辑题目 #${question.id}`);
  renderQuestionList(questionCache);
}

function resetQuestionForm() {
  editingQuestionId = null;
  $("questionForm").reset();
  $("questionFormTitle").textContent = "新增题目";
  $("questionFormMeta").textContent = "保存后可直接练习";
  $("createQuestionBtn").textContent = "保存题目";
  $("cancelEditBtn").hidden = true;
  syncCreateFormDefaults();
  renderQuestionList(questionCache);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function seedQuestions() {
  const result = await request("/api/questions/seed", { method: "POST" });
  setStatus(result.created > 0 ? `已新增 ${result.created} 道题` : "题库已是最新");
  await refreshQuestionCount();
}

async function loadPracticeQuestion() {
  const qs = queryString(selectedFilters());
  practiceQuestion = await request(`/api/practice/question${qs ? `?${qs}` : ""}`);
  renderQuestion($("practiceQuestion"), practiceQuestion);
  $("practiceAnswer").value = "";
  updateAnswerMeta("practiceAnswer", "practiceAnswerMeta");
  $("practiceResult").classList.add("empty");
  $("practiceResult").textContent = "提交答案后显示评分、反馈和参考答案。";
  $("practiceMeta").textContent = `题目 #${practiceQuestion.id}`;
  updatePracticeSummary();
  setStatus("已抽取练习题");
}

async function saveQuestion(event) {
  event.preventDefault();
  const rubric = $("newRubric")
    .value.split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
  const payload = {
    category: $("newCategory").value.trim(),
    difficulty: $("newDifficulty").value.trim(),
    question: $("newQuestion").value.trim(),
    standard_answer: $("newStandardAnswer").value.trim(),
    rubric,
  };

  if (!payload.category || !payload.difficulty || !payload.question || !payload.standard_answer) {
    setStatus("请填写分类、难度、题目和参考答案");
    return;
  }

  const saved = await request(editingQuestionId ? `/api/questions/${editingQuestionId}` : "/api/questions", {
    method: editingQuestionId ? "PUT" : "POST",
    body: JSON.stringify(payload),
  });

  const wasEditing = editingQuestionId !== null;
  resetQuestionForm();
  $("category").value = saved.category;
  $("difficulty").value = saved.difficulty;
  await refreshQuestionCount();
  useQuestionForPractice(saved);
  setStatus(wasEditing ? `已更新题目 #${saved.id}` : `已新增题目 #${saved.id}`);
}

async function deleteQuestion(questionId) {
  const question = questionCache.find((item) => item.id === questionId);
  const confirmed = window.confirm(`确认删除题目 #${questionId}？\n${question ? question.question : ""}`);
  if (!confirmed) return;

  await request(`/api/questions/${questionId}`, { method: "DELETE" });
  if (practiceQuestion?.id === questionId) {
    practiceQuestion = null;
    $("practiceQuestion").classList.add("empty");
    $("practiceQuestion").textContent = "当前练习题已删除，请重新选择题目。";
    $("practiceMeta").textContent = "未开始";
    updatePracticeSummary();
  }
  if (editingQuestionId === questionId) resetQuestionForm();
  await refreshQuestionCount();
  setStatus(`已删除题目 #${questionId}`);
}

async function submitPracticeAnswer() {
  if (!practiceQuestion) {
    setStatus("请先抽一道题");
    return;
  }
  const answer = $("practiceAnswer").value.trim();
  if (!answer) {
    setStatus("请先输入回答");
    return;
  }
  const result = await request("/api/practice/answer", {
    method: "POST",
    body: JSON.stringify({ question_id: practiceQuestion.id, answer }),
  });
  renderPracticeResult(result);
  setStatus("练习答案已评分");
}

async function startInterview() {
  const payload = selectedInterviewConfig();
  if (!payload.category) payload.category = null;
  if (!payload.difficulty) payload.difficulty = null;
  const result = await request("/api/interview/sessions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  interviewSessionId = result.session_id;
  interviewFinished = false;
  interviewLogs = [];
  renderQuestion($("interviewQuestion"), result.current_question);
  $("interviewAnswer").value = "";
  updateAnswerMeta("interviewAnswer", "interviewAnswerMeta");
  $("interviewResult").classList.remove("empty");
  renderInterviewLogs();
  updateInterviewProgress(result.answered_count, result.total_questions);
  updateInterviewConfigSummary();
  setStatus("模拟面试已开始");
}

async function submitInterviewAnswer() {
  if (!interviewSessionId || interviewFinished) {
    setStatus("请先开始一场新的面试");
    return;
  }
  const answer = $("interviewAnswer").value.trim();
  if (!answer) {
    setStatus("请先输入回答");
    return;
  }
  const result = await request(`/api/interview/sessions/${interviewSessionId}/answer`, {
    method: "POST",
    body: JSON.stringify({ answer }),
  });
  interviewLogs.push({
    index: result.answered_count,
    score: result.score,
    answer,
    feedback: result.feedback,
    standardAnswer: result.standard_answer,
  });
  renderInterviewLogs();
  updateInterviewProgress(result.answered_count, result.total_questions);
  $("interviewAnswer").value = "";
  updateAnswerMeta("interviewAnswer", "interviewAnswerMeta");

  if (result.is_finished) {
    interviewFinished = true;
    $("interviewQuestion").textContent = "本轮面试已结束，可以查看右侧报告。";
    $("interviewQuestion").classList.add("empty");
    const report = await request(`/api/interview/sessions/${interviewSessionId}/report`);
    renderInterviewLogs(report);
    setStatus("模拟面试已完成");
    return;
  }

  renderQuestion($("interviewQuestion"), result.next_question);
  setStatus("已进入下一题");
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".view").forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      $(`${tab.dataset.tab}View`).classList.add("active");
    });
  });
}

function bindActions() {
  $("seedBtn").addEventListener("click", () => runAction(seedQuestions, "正在初始化题库..."));
  $("refreshBtn").addEventListener("click", () => runAction(refreshQuestionCount, "正在刷新题库..."));
  $("loadPracticeBtn").addEventListener("click", () =>
    runAction(loadPracticeQuestion, "正在抽题..."),
  );
  $("submitPracticeBtn").addEventListener("click", () =>
    runAction(submitPracticeAnswer, "正在评分..."),
  );
  $("startInterviewBtn").addEventListener("click", () => runAction(startInterview, "正在创建模拟面试..."));
  $("submitInterviewBtn").addEventListener("click", () =>
    runAction(submitInterviewAnswer, "正在提交面试回答..."),
  );
  $("category").addEventListener("change", () => runAction(refreshQuestionCount, "正在刷新题库..."));
  $("difficulty").addEventListener("change", () => runAction(refreshQuestionCount, "正在刷新题库..."));
  $("category").addEventListener("change", updateInterviewConfigSummary);
  $("difficulty").addEventListener("change", updateInterviewConfigSummary);
  $("interviewQuestionCount").addEventListener("change", updateInterviewConfigSummary);
  $("practiceAnswer").addEventListener("input", () => updateAnswerMeta("practiceAnswer", "practiceAnswerMeta"));
  $("interviewAnswer").addEventListener("input", () => updateAnswerMeta("interviewAnswer", "interviewAnswerMeta"));
  $("category").addEventListener("change", syncCreateFormDefaults);
  $("difficulty").addEventListener("change", syncCreateFormDefaults);
  $("questionForm").addEventListener("submit", (event) => runAction(() => saveQuestion(event), "正在保存题目..."));
  $("cancelEditBtn").addEventListener("click", () => {
    resetQuestionForm();
    setStatus("已取消编辑");
  });
  $("questionList").addEventListener("click", (event) => {
    const practiceButton = event.target.closest("[data-practice-id]");
    const editButton = event.target.closest("[data-edit-id]");
    const deleteButton = event.target.closest("[data-delete-id]");

    if (practiceButton) {
      const question = questionCache.find((item) => item.id === Number(practiceButton.dataset.practiceId));
      if (question) useQuestionForPractice(question);
      return;
    }
    if (editButton) {
      const question = questionCache.find((item) => item.id === Number(editButton.dataset.editId));
      if (question) fillQuestionForm(question);
      return;
    }
    if (deleteButton) {
      runAction(() => deleteQuestion(Number(deleteButton.dataset.deleteId)), "正在删除题目...");
    }
  });
}

bindTabs();
bindActions();
syncCreateFormDefaults();
updateFilterSummary();
updatePracticeSummary();
updateInterviewConfigSummary();
updateAnswerMeta("practiceAnswer", "practiceAnswerMeta");
updateAnswerMeta("interviewAnswer", "interviewAnswerMeta");
refreshConfigStatus().catch(() => {
  $("scoringMode").textContent = "评分：状态未知";
});
runAction(seedQuestions, "正在初始化题库...");
