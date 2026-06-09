import {
  analyzeUploadedResume,
  deleteQuestionRequest,
  deleteResumeHistoryRequest,
  getConfigStatus,
  getInterviewReport,
  getPracticeQuestion,
  getResumeResult,
  importJobsJsonl,
  listResumeHistory,
  listJobs,
  listQuestions,
  rebuildJobVectorIndex,
  saveQuestionRequest,
  seedQuestionBank,
  startInterviewSession,
  submitInterviewAnswerRequest,
  uploadResumeDocument,
} from "./api.js?v=20260609-rag-7";
import {
  renderFilterOptions,
  renderInterviewLogs,
  renderJobCollectResult,
  renderJobList,
  renderJobPending,
  renderJobVectorStatus,
  renderPracticePending,
  renderPracticeResult,
  renderQuestion,
  renderQuestionCount,
  renderQuestionList,
  renderResumeError,
  renderResumeHistory,
  renderResumePending,
  renderResumeResult,
  updateAnswerMeta,
  updateFilterSummary,
  updateInterviewConfigSummary,
  updateInterviewProgress,
  updatePracticeSummary,
} from "./render.js?v=20260609-rag-7";
import { state } from "./state.js?v=20260609-rag-7";
import { $, escapeHtml, isChoiceType, parseError } from "./utils.js?v=20260609-rag-7";

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

function syncCreateFormDefaults() {
  if ($("category").value && !$("newCategory").value) $("newCategory").value = $("category").value;
  if ($("difficulty").value && !$("newDifficulty").value) $("newDifficulty").value = $("difficulty").value;
}

function setStatus(text) {
  $("statusText").textContent = text;
}

function setBusy(isBusy) {
  state.busyCount += isBusy ? 1 : -1;
  state.busyCount = Math.max(state.busyCount, 0);
  document.querySelectorAll("button").forEach((button) => {
    button.disabled = state.busyCount > 0;
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

async function refreshConfigStatus() {
  const config = await getConfigStatus();
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

async function refreshQuestionCount() {
  const filters = selectedFilters();
  const [questions, allQuestions] = await Promise.all([
    listQuestions(filters),
    listQuestions(),
  ]);
  state.questionCache = questions;
  renderQuestionCount(questions, allQuestions);
  renderQuestionList(questions);
  renderFilterOptions(allQuestions);
  updateFilterSummary(selectedFilters());
}

async function seedQuestions() {
  const result = await seedQuestionBank();
  setStatus(result.created > 0 ? `已新增 ${result.created} 道题` : "题库已是最新");
  await refreshQuestionCount();
}

async function loadPracticeQuestion() {
  state.practiceQuestion = await getPracticeQuestion(selectedFilters());
  renderSelectedPracticeQuestion("已抽取练习题");
}

function useQuestionForPractice(question) {
  state.practiceQuestion = question;
  renderSelectedPracticeQuestion("已选择题库中的题目");
}

function renderSelectedPracticeQuestion(statusText) {
  renderQuestion($("practiceQuestion"), state.practiceQuestion);
  $("practiceAnswer").value = "";
  renderAnswerInputForQuestion(state.practiceQuestion);
  updateAnswerMeta("practiceAnswer", "practiceAnswerMeta");
  $("practiceResult").classList.add("empty");
  $("practiceResult").textContent = "提交答案后显示评分、反馈和参考答案。";
  $("practiceMeta").textContent = `题目 #${state.practiceQuestion.id}`;
  updatePracticeSummary();
  setStatus(statusText);
  renderQuestionList(state.questionCache);
}

function fillQuestionForm(question) {
  state.editingQuestionId = question.id;
  $("newCategory").value = question.category;
  $("newDifficulty").value = question.difficulty;
  $("newQuestionType").value = question.question_type || "short_answer";
  $("newQuestion").value = question.question;
  $("newStandardAnswer").value = question.standard_answer;
  $("newRubric").value = question.rubric.join("\n");
  $("newOptions").value = (question.options || []).join("\n");
  $("newCorrectAnswer").value = question.correct_answer || "";
  toggleQuestionTypeFields();
  $("questionFormTitle").textContent = `编辑题目 #${question.id}`;
  $("questionFormMeta").textContent = "保存后会更新题库列表";
  $("createQuestionBtn").textContent = "保存修改";
  $("cancelEditBtn").hidden = false;
  setStatus(`正在编辑题目 #${question.id}`);
  renderQuestionList(state.questionCache);
}

function resetQuestionForm() {
  state.editingQuestionId = null;
  $("questionForm").reset();
  $("questionFormTitle").textContent = "新增题目";
  $("questionFormMeta").textContent = "保存后可直接练习";
  $("createQuestionBtn").textContent = "保存题目";
  $("cancelEditBtn").hidden = true;
  toggleQuestionTypeFields();
  syncCreateFormDefaults();
  renderQuestionList(state.questionCache);
}

async function saveQuestion(event) {
  event.preventDefault();
  const payload = buildQuestionPayload();

  if (!payload.category || !payload.difficulty || !payload.question || !payload.standard_answer) {
    setStatus("请填写分类、难度、题目和参考答案");
    return;
  }
  if (isChoiceType(payload.question_type) && (!payload.options.length || !payload.correct_answer)) {
    setStatus("选择题需要填写选项和正确答案");
    return;
  }

  const saved = await saveQuestionRequest(state.editingQuestionId, payload);
  const wasEditing = state.editingQuestionId !== null;
  resetQuestionForm();
  $("category").value = saved.category;
  $("difficulty").value = saved.difficulty;
  await refreshQuestionCount();
  useQuestionForPractice(saved);
  setStatus(wasEditing ? `已更新题目 #${saved.id}` : `已新增题目 #${saved.id}`);
}

function buildQuestionPayload() {
  return {
    category: $("newCategory").value.trim(),
    difficulty: $("newDifficulty").value.trim(),
    question_type: $("newQuestionType").value,
    question: $("newQuestion").value.trim(),
    standard_answer: $("newStandardAnswer").value.trim(),
    rubric: splitLines($("newRubric").value),
    options: splitLines($("newOptions").value),
    correct_answer: $("newCorrectAnswer").value.trim() || null,
  };
}

function splitLines(value) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

async function deleteQuestion(questionId) {
  const question = state.questionCache.find((item) => item.id === questionId);
  const confirmed = window.confirm(`确认删除题目 #${questionId}？\n${question ? question.question : ""}`);
  if (!confirmed) return;

  await deleteQuestionRequest(questionId);
  if (state.practiceQuestion?.id === questionId) {
    state.practiceQuestion = null;
    $("practiceQuestion").classList.add("empty");
    $("practiceQuestion").textContent = "当前练习题已删除，请重新选择题目。";
    $("practiceMeta").textContent = "未开始";
    updatePracticeSummary();
  }
  if (state.editingQuestionId === questionId) resetQuestionForm();
  await refreshQuestionCount();
  setStatus(`已删除题目 #${questionId}`);
}

async function submitPracticeAnswer() {
  if (!state.practiceQuestion) {
    setStatus("请先抽一道题");
    return;
  }
  const answer = getPracticeAnswer();
  if (!answer) {
    setStatus("请先输入回答");
    return;
  }
  await streamPracticeAnswer(answer);
}

function renderAnswerInputForQuestion(question) {
  const choiceBox = $("choiceAnswerBox");
  if (isChoiceType(question.question_type)) {
    $("practiceAnswer").hidden = true;
    choiceBox.hidden = false;
    const inputType = question.question_type === "multiple_choice" ? "checkbox" : "radio";
    choiceBox.innerHTML = (question.options || [])
      .map((option, index) => {
        const value = option.split(".")[0].trim() || option;
        return `
          <label class="choice-answer-option">
            <input type="${inputType}" name="choiceAnswer" value="${escapeHtml(value)}" ${index === 0 && inputType === "radio" ? "checked" : ""} />
            <span>${escapeHtml(option)}</span>
          </label>
        `;
      })
      .join("");
    return;
  }

  $("practiceAnswer").hidden = false;
  choiceBox.hidden = true;
  choiceBox.innerHTML = "";
}

function getPracticeAnswer() {
  if (state.practiceQuestion?.question_type === "single_choice") {
    return document.querySelector('input[name="choiceAnswer"]:checked')?.value || "";
  }
  if (state.practiceQuestion?.question_type === "multiple_choice") {
    return [...document.querySelectorAll('input[name="choiceAnswer"]:checked')]
      .map((item) => item.value)
      .join(",");
  }
  return $("practiceAnswer").value.trim();
}

async function streamPracticeAnswer(answer) {
  renderPracticePending("已提交答案，正在等待评分服务响应。");
  setStatus("正在评分...");
  const response = await fetch("/api/practice/answer/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: state.practiceQuestion.id, answer }),
  });
  if (!response.ok || !response.body) {
    throw new Error(await response.text());
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    parts.forEach(handleSseMessage);
  }
}

function handleSseMessage(raw) {
  const event = raw.match(/^event: (.+)$/m)?.[1];
  const dataText = raw.match(/^data: (.+)$/m)?.[1];
  if (!event || !dataText) return;
  const payload = JSON.parse(dataText);
  if (event === "progress") {
    renderPracticePending(payload.message || "正在评分...");
    setStatus(payload.message || "正在评分...");
  }
  if (event === "result") {
    renderPracticeResult(payload);
    setStatus("练习答案已评分");
  }
}

function toggleQuestionTypeFields() {
  const isChoice = isChoiceType($("newQuestionType").value);
  $("choiceQuestionFields").hidden = !isChoice;
}

async function startInterview() {
  const payload = selectedInterviewConfig();
  if (!payload.category) payload.category = null;
  if (!payload.difficulty) payload.difficulty = null;
  const result = await startInterviewSession(payload);
  state.interviewSessionId = result.session_id;
  state.interviewFinished = false;
  state.interviewLogs = [];
  renderQuestion($("interviewQuestion"), result.current_question);
  $("interviewAnswer").value = "";
  updateAnswerMeta("interviewAnswer", "interviewAnswerMeta");
  $("interviewResult").classList.remove("empty");
  renderInterviewLogs();
  updateInterviewProgress(result.answered_count, result.total_questions);
  updateInterviewConfigSummary(selectedInterviewConfig());
  setStatus("模拟面试已开始");
}

async function submitInterviewAnswer() {
  if (!state.interviewSessionId || state.interviewFinished) {
    setStatus("请先开始一场新的面试");
    return;
  }
  const answer = $("interviewAnswer").value.trim();
  if (!answer) {
    setStatus("请先输入回答");
    return;
  }
  const result = await submitInterviewAnswerRequest(state.interviewSessionId, answer);
  state.interviewLogs.push({
    index: result.answered_count,
    score: result.score,
    source: result.source,
    answer,
    feedback: result.feedback,
    strengths: result.strengths,
    weaknesses: result.weaknesses,
    suggestions: result.suggestions,
    standardAnswer: result.standard_answer,
  });
  renderInterviewLogs();
  updateInterviewProgress(result.answered_count, result.total_questions);
  $("interviewAnswer").value = "";
  updateAnswerMeta("interviewAnswer", "interviewAnswerMeta");

  if (result.is_finished) {
    state.interviewFinished = true;
    $("interviewQuestion").textContent = "本轮面试已结束，可以查看右侧报告。";
    $("interviewQuestion").classList.add("empty");
    const report = await getInterviewReport(state.interviewSessionId);
    renderInterviewLogs(report);
    setStatus("模拟面试已完成");
    return;
  }

  renderQuestion($("interviewQuestion"), result.next_question);
  setStatus("已进入下一题");
}

async function submitResumeAnalyze(event) {
  event.preventDefault();
  const file = $("resumeFile").files?.[0];
  if (!file) {
    setStatus("请先选择 PDF 或 DOCX 简历");
    return;
  }
  if (!isResumeDocument(file.name)) {
    setStatus("当前支持上传 PDF 或 DOCX 简历");
    return;
  }

  renderResumePending("正在提取文字", "正在读取简历文档并抽取可分析文本。");
  let progressTimer = null;
  try {
    const uploaded = await uploadResumeDocument(file);
    const messages = [
      `已提取 ${uploaded.extracted_chars} 个字符，正在用 Chroma 召回 Top 8 相似 JD。`,
      "正在压缩候选岗位上下文，保留岗位要求、命中证据和能力缺口。",
      "正在请求 LLM 结合简历和候选 JD 完成岗位画像，并选出最值得优先准备的 Top 3。",
      "LLM 正在生成面试准备建议；如果响应超时，会自动回退到本地 mock 分析。",
      "LLM 分析仍在进行中，请稍等，完成后会自动保存到历史结果。",
    ];
    let messageIndex = 0;
    renderResumePending("文字提取完成，正在检索岗位知识库", messages[messageIndex]);
    progressTimer = window.setInterval(() => {
      messageIndex = Math.min(messageIndex + 1, messages.length - 1);
      renderResumePending("正在生成岗位画像", messages[messageIndex]);
    }, 4500);
    const result = await analyzeUploadedResume(uploaded.resume_id);
    window.clearInterval(progressTimer);
    progressTimer = null;
    renderResumeResult(result);
    await refreshResumeHistory();
    setStatus("简历分析完成");
  } catch (error) {
    if (progressTimer) window.clearInterval(progressTimer);
    const message = parseError(error.message || String(error));
    renderResumeError(message);
    throw new Error(message);
  }
}

function isResumeDocument(filename) {
  const lower = filename.toLowerCase();
  return lower.endsWith(".pdf") || lower.endsWith(".docx");
}

async function refreshResumeHistory() {
  state.resumeHistory = await listResumeHistory();
  renderResumeHistory(state.resumeHistory);
}

async function showResumeHistoryResult(resumeId) {
  const result = await getResumeResult(resumeId);
  renderResumeResult(result);
  setStatus(`已加载简历 #${resumeId} 的历史分析`);
}

async function deleteResumeHistory(resumeId) {
  const item = state.resumeHistory.find((historyItem) => historyItem.resume_id === resumeId);
  const filename = item?.filename || `简历 #${resumeId}`;
  const confirmed = window.confirm(`确认删除历史结果？\n${filename}\n\n删除后会同时移除这份简历文本和分析结果。`);
  if (!confirmed) return;

  await deleteResumeHistoryRequest(resumeId);
  await refreshResumeHistory();
  $("resumeResult").classList.add("empty");
  $("resumeResult").textContent = "历史结果已删除。上传 PDF 或 DOCX 简历后，这里会分阶段显示文字提取进度、分析进度和最终建议。";
  setStatus(`已删除历史结果：${filename}`);
}

async function refreshJobList() {
  state.jobs = await listJobs({ q: state.jobSearchQuery });
  renderJobList(state.jobs);
}

async function submitJobSearch(event) {
  event.preventDefault();
  state.jobSearchQuery = $("jobSearchInput").value.trim();
  await refreshJobList();
  setStatus(state.jobSearchQuery ? `已按关键词筛选岗位：${state.jobSearchQuery}` : "已显示全部岗位");
}

async function clearJobSearch() {
  state.jobSearchQuery = "";
  $("jobSearchInput").value = "";
  await refreshJobList();
  setStatus("已重置岗位搜索");
}

function timeoutAfter(ms, message) {
  return new Promise((_, reject) => {
    window.setTimeout(() => reject(new Error(message)), ms);
  });
}

async function fetchJobVectorStatusDirect() {
  const response = await fetch("/api/jobs/vector-index/status", {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json();
}

async function refreshJobVectorStatus({ showPending = false } = {}) {
  const target = $("jobVectorStatus");
  if (!target) return;
  if (showPending) renderJobVectorStatus(null, "正在读取索引状态...");

  try {
    state.jobVectorStatus = await Promise.race([
      fetchJobVectorStatusDirect(),
      timeoutAfter(5000, "索引状态读取超时，请稍后重试或点击重建索引"),
    ]);
    renderJobVectorStatus(state.jobVectorStatus);
  } catch (error) {
    target.textContent = `索引状态读取失败：${parseError(error.message || String(error))}`;
  }
}

async function rebuildJobVector() {
  if (!$("jobVectorStatus")) return;
  renderJobVectorStatus(null, "正在重建岗位向量索引...");
  state.jobVectorStatus = await rebuildJobVectorIndex();
  renderJobVectorStatus(state.jobVectorStatus);
  setStatus(`岗位索引已重建，覆盖 ${state.jobVectorStatus.job_count} 个岗位`);
}

async function submitJobCollect(event) {
  event.preventDefault();
  const file = $("jobJsonlFile").files?.[0];
  if (!file) {
    setStatus("请先选择岗位 JSONL 文件");
    return;
  }
  if (!file.name.toLowerCase().endsWith(".jsonl")) {
    setStatus("当前只支持导入 .jsonl 岗位数据文件");
    return;
  }

  renderJobPending("正在读取 JSONL 文件并写入岗位知识库。");
  const result = await importJobsJsonl(file);
  renderJobCollectResult(result);
  await refreshJobList();
  await rebuildJobVector();
  setStatus(`岗位导入完成，新增 ${result.created_count} 条，更新 ${result.updated_count} 条`);
}

function bindTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".view").forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      $(`${tab.dataset.tab}View`).classList.add("active");
      if (tab.dataset.tab === "jobs") {
        refreshJobVectorStatus({ showPending: !state.jobVectorStatus });
      }
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
  $("category").addEventListener("change", () => updateInterviewConfigSummary(selectedInterviewConfig()));
  $("difficulty").addEventListener("change", () => updateInterviewConfigSummary(selectedInterviewConfig()));
  $("interviewQuestionCount").addEventListener("change", () => updateInterviewConfigSummary(selectedInterviewConfig()));
  $("practiceAnswer").addEventListener("input", () => updateAnswerMeta("practiceAnswer", "practiceAnswerMeta"));
  $("interviewAnswer").addEventListener("input", () => updateAnswerMeta("interviewAnswer", "interviewAnswerMeta"));
  $("category").addEventListener("change", syncCreateFormDefaults);
  $("difficulty").addEventListener("change", syncCreateFormDefaults);
  $("questionForm").addEventListener("submit", (event) => runAction(() => saveQuestion(event), "正在保存题目..."));
  $("resumeForm").addEventListener("submit", (event) => runAction(() => submitResumeAnalyze(event), "正在分析简历..."));
  $("jobCollectForm").addEventListener("submit", (event) => runAction(() => submitJobCollect(event), "正在导入岗位数据..."));
  $("jobSearchForm").addEventListener("submit", (event) => runAction(() => submitJobSearch(event), "正在搜索岗位..."));
  $("clearJobSearchBtn").addEventListener("click", () => runAction(clearJobSearch, "正在重置岗位搜索..."));
  $("rebuildJobVectorBtn")?.addEventListener("click", () => runAction(rebuildJobVector, "正在重建岗位索引..."));
  $("resumeHistory").addEventListener("click", (event) => {
    const button = event.target.closest("[data-resume-id]");
    if (button) {
      runAction(() => showResumeHistoryResult(Number(button.dataset.resumeId)), "正在加载历史分析...");
      return;
    }
    const deleteButton = event.target.closest("[data-delete-resume-id]");
    if (deleteButton) {
      runAction(() => deleteResumeHistory(Number(deleteButton.dataset.deleteResumeId)), "正在删除历史结果...");
    }
  });
  $("newQuestionType").addEventListener("change", toggleQuestionTypeFields);
  $("cancelEditBtn").addEventListener("click", () => {
    resetQuestionForm();
    setStatus("已取消编辑");
  });
  $("questionList").addEventListener("click", (event) => {
    const practiceButton = event.target.closest("[data-practice-id]");
    const editButton = event.target.closest("[data-edit-id]");
    const deleteButton = event.target.closest("[data-delete-id]");

    if (practiceButton) {
      const question = state.questionCache.find((item) => item.id === Number(practiceButton.dataset.practiceId));
      if (question) useQuestionForPractice(question);
      return;
    }
    if (editButton) {
      const question = state.questionCache.find((item) => item.id === Number(editButton.dataset.editId));
      if (question) fillQuestionForm(question);
      return;
    }
    if (deleteButton) {
      runAction(() => deleteQuestion(Number(deleteButton.dataset.deleteId)), "正在删除题目...");
    }
  });
}

function boot() {
  bindTabs();
  bindActions();
  syncCreateFormDefaults();
  updateFilterSummary(selectedFilters());
  updatePracticeSummary();
  updateInterviewConfigSummary(selectedInterviewConfig());
  updateAnswerMeta("practiceAnswer", "practiceAnswerMeta");
  updateAnswerMeta("interviewAnswer", "interviewAnswerMeta");
  toggleQuestionTypeFields();
  refreshConfigStatus().catch(() => {
    $("scoringMode").textContent = "评分：状态未知";
  });
  refreshResumeHistory().catch(() => {
    $("resumeHistory").textContent = "历史记录加载失败。";
  });
  refreshJobList().catch(() => {
    $("jobList").textContent = "岗位数据加载失败。";
  });
  window.setTimeout(() => refreshJobVectorStatus({ showPending: true }), 0);
  runAction(seedQuestions, "正在初始化题库...");
}

boot();
