import {
  analyzeUploadedResume,
  deleteResumeHistoryRequest,
  getConfigStatus,
  getHrInterviewReport,
  getPracticeQuestion,
  getResumeResult,
  importJobsJsonl,
  listHrInterviewSessions,
  listResumeHistory,
  listJobs,
  listQuestions,
  rebuildJobVectorIndex,
  seedQuestionBank,
  startHrInterviewStream,
  submitHrInterviewAnswerStream,
  uploadResumeDocument,
} from "./api.js?v=20260610-practice-3";
import {
  renderFilterOptions,
  renderInterviewLogs,
  renderInterviewSessions,
  renderJobCollectResult,
  renderJobList,
  renderJobPending,
  renderJobVectorStatus,
  renderPracticePending,
  renderPracticeResult,
  renderHrQuestion,
  renderHrStreamText,
  renderHrTurnStream,
  renderHrTurnSummary,
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
  updateInterviewRecordsLayout,
  updatePracticeSummary,
} from "./render.js?v=20260610-practice-3";
import { state } from "./state.js?v=20260610-practice-3";
import { $, escapeHtml, isChoiceType, parseError } from "./utils.js?v=20260610-practice-3";

function selectedFilters() {
  return {
    category: $("category").value,
    difficulty: $("difficulty").value,
  };
}

function selectedInterviewConfig() {
  const resumeOption = $("hrResumeSelect").selectedOptions[0];
  const jobOption = $("hrJobSelect").selectedOptions[0];
  return {
    resume_id: Number($("hrResumeSelect").value) || null,
    job_id: Number($("hrJobSelect").value) || null,
    resumeLabel: resumeOption?.textContent || "",
    jobLabel: jobOption?.textContent || "",
    total_questions: Number($("interviewQuestionCount").value),
  };
}

function shortOptionLabel(...parts) {
  const value = parts.filter(Boolean).join(" · ");
  return value.length > 34 ? `${value.slice(0, 34)}...` : value;
}

function setStatus(text) {
  $("statusText").textContent = text;
}

function setBusy(isBusy) {
  state.busyCount += isBusy ? 1 : -1;
  state.busyCount = Math.max(state.busyCount, 0);
  document.querySelectorAll("button:not(.tab):not([data-static-disabled])").forEach((button) => {
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

function refreshHrInterviewOptions() {
  const resumeSelect = $("hrResumeSelect");
  const jobSelect = $("hrJobSelect");
  if (!resumeSelect || !jobSelect) return;

  const currentResume = resumeSelect.value;
  const currentJob = jobSelect.value;
  const analyzedResumes = state.resumeHistory.filter((item) => item.latest_analysis);

  resumeSelect.innerHTML = [
    '<option value="">选择一份已分析简历</option>',
    ...analyzedResumes.map((item) => {
      const role = item.latest_analysis?.target_roles?.[0] || "未识别岗位";
      return `<option value="${item.resume_id}">${escapeHtml(item.filename)} · ${escapeHtml(role)}</option>`;
    }),
  ].join("");
  resumeSelect.value = analyzedResumes.some((item) => String(item.resume_id) === currentResume)
    ? currentResume
    : String(analyzedResumes[0]?.resume_id || "");

  jobSelect.innerHTML = [
    '<option value="">选择一个目标岗位</option>',
    ...state.jobs.map((job) => {
      const label = shortOptionLabel(job.company, job.title);
      return `<option value="${job.id}" title="${escapeHtml(job.company)} · ${escapeHtml(job.title)}">${escapeHtml(label)}</option>`;
    }),
  ].join("");
  jobSelect.value = state.jobs.some((job) => String(job.id) === currentJob)
    ? currentJob
    : String(state.jobs[0]?.id || "");
  updateInterviewConfigSummary(selectedInterviewConfig());
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
  const practicePanel = document.querySelector(".practice-session-panel");
  const isChoice = isChoiceType(question.question_type);
  practicePanel?.classList.toggle("choice-mode", isChoice);
  if (isChoice) {
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

  await readSseResponse(response, handlePracticeSseEvent);
}

async function readSseResponse(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      await handleSseMessage(part, onEvent);
    }
  }
  if (buffer.trim()) {
    await handleSseMessage(buffer, onEvent);
  }
}

async function handleSseMessage(raw, onEvent) {
  const event = raw.match(/^event: (.+)$/m)?.[1];
  const dataText = raw
    .split("\n")
    .filter((line) => line.startsWith("data: "))
    .map((line) => line.slice(6))
    .join("\n");
  if (!event || !dataText) return;
  const payload = JSON.parse(dataText);
  if (event === "error") {
    throw new Error(payload.message || "流式响应失败，请稍后重试");
  }
  await onEvent(event, payload);
}

function handlePracticeSseEvent(event, payload) {
  if (event === "progress") {
    renderPracticePending(payload.message || "正在评分...");
    setStatus(payload.message || "正在评分...");
  }
  if (event === "result") {
    renderPracticeResult(payload);
    setStatus("练习答案已评分");
  }
}

async function startInterview() {
  const payload = selectedInterviewConfig();
  await startHrInterview(payload);
}

async function startHrInterview(payload) {
  if (!payload.resume_id || !payload.job_id) {
    setStatus("请先选择一份已分析简历和一个目标岗位");
    return;
  }
  let questionText = "";
  renderHrStreamText($("interviewQuestion"), "面试官正在生成第一题", "", {
    company: payload.jobLabel || "目标岗位",
    job_title: "岗位 HR 面试",
    resume_filename: payload.resumeLabel || "已选择简历",
  });
  $("interviewResult").classList.remove("empty");
  $("interviewResult").textContent = "面试开始后，这里会显示每题反馈和最终报告。";
  const response = await startHrInterviewStream({
    resume_id: payload.resume_id,
    job_id: payload.job_id,
    total_questions: payload.total_questions,
  });

  await readSseResponse(response, (event, eventPayload) => {
    if (event === "progress") {
      setStatus(eventPayload.message || "正在生成岗位 HR 面试题...");
      return;
    }
    if (event === "delta" && eventPayload.target === "question") {
      questionText += eventPayload.text || "";
      renderHrStreamText($("interviewQuestion"), "面试官正在生成第一题", questionText, {
        company: payload.jobLabel || "目标岗位",
        job_title: "岗位 HR 面试",
        resume_filename: payload.resumeLabel || "已选择简历",
      });
      return;
    }
    if (event === "result") {
      state.interviewSessionId = eventPayload.session_id;
      state.hrInterviewContext = eventPayload.context;
      state.hrCurrentQuestion = eventPayload.current_question;
      state.interviewFinished = false;
      state.interviewLogs = [];
      state.selectedInterviewReport = null;
      state.interviewRecordsExpanded = false;
      updateInterviewRecordsLayout();
      renderHrQuestion($("interviewQuestion"), eventPayload.current_question, eventPayload.context);
      $("interviewAnswer").value = "";
      $("interviewResult").classList.remove("empty");
      renderInterviewLogs();
      refreshInterviewSessions().catch(() => {});
      updateInterviewProgress(eventPayload.answered_count, eventPayload.total_questions);
      updateInterviewConfigSummary(selectedInterviewConfig());
      setStatus("岗位 HR 面试已开始");
    }
  });
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
  await submitHrInterviewAnswer(answer);
}

async function submitHrInterviewAnswer(answer) {
  const currentQuestion = state.hrCurrentQuestion;
  let feedbackText = "";
  let nextQuestionText = "";
  const liveTurn = {
    context: state.hrInterviewContext,
    question: currentQuestion?.question || "",
    answer,
    feedbackText,
    nextQuestionText,
  };
  renderHrTurnStream($("interviewQuestion"), liveTurn);
  setStatus("面试官正在反馈...");
  const response = await submitHrInterviewAnswerStream(state.interviewSessionId, answer);
  $("interviewAnswer").value = "";

  await readSseResponse(response, async (event, eventPayload) => {
    if (event === "progress") {
      setStatus(eventPayload.message || "面试官正在反馈...");
      return;
    }
    if (event === "delta" && eventPayload.target === "feedback") {
      feedbackText += eventPayload.text || "";
      setStatus("面试官正在记录本轮评价...");
      return;
    }
    if (event === "delta" && eventPayload.target === "next_question") {
      nextQuestionText += eventPayload.text || "";
      renderHrTurnStream($("interviewQuestion"), {
        ...liveTurn,
        feedbackText,
        nextQuestionText,
      });
      return;
    }
    if (event === "result") {
      const turn = {
        index: eventPayload.answered_count,
        score: eventPayload.score,
        source: eventPayload.source,
        question: currentQuestion?.question || "",
        focus: currentQuestion?.focus || [],
        answer,
        feedback: eventPayload.feedback,
        strengths: eventPayload.strengths,
        weaknesses: eventPayload.weaknesses,
        suggestions: eventPayload.suggestions,
        passScore: eventPayload.pass_score,
        passed: eventPayload.passed,
        terminationReason: eventPayload.termination_reason,
        standardAnswer: "岗位 HR 面试没有固定参考答案，请优先参考反馈中的岗位匹配建议。",
      };
      state.interviewLogs.push(turn);
      renderInterviewLogs();
      updateInterviewProgress(eventPayload.answered_count, eventPayload.total_questions);

      if (eventPayload.is_finished) {
        state.interviewFinished = true;
        state.hrCurrentQuestion = null;
        renderHrTurnSummary($("interviewQuestion"), turn);
        const report = await getHrInterviewReport(state.interviewSessionId);
        renderInterviewLogs(report);
        await refreshInterviewSessions();
        setStatus(eventPayload.termination_reason ? "面试已提前终止，记录已保存" : "岗位 HR 面试已完成，记录已保存");
        return;
      }

      state.hrCurrentQuestion = eventPayload.next_question;
      renderHrQuestion($("interviewQuestion"), eventPayload.next_question, state.hrInterviewContext);
      refreshInterviewSessions().catch(() => {});
      setStatus("岗位 HR 面试已进入下一题");
    }
  });
}

async function refreshInterviewSessions() {
  state.hrInterviewSessions = await listHrInterviewSessions();
  renderInterviewSessions(state.hrInterviewSessions);
}

async function showInterviewReport(sessionId) {
  const report = await getHrInterviewReport(sessionId);
  state.selectedInterviewReport = report;
  state.interviewRecordsExpanded = true;
  updateInterviewRecordsLayout();
  renderInterviewLogs(report);
  setStatus(`已加载面试 #${sessionId} 的完整记录`);
}

function setInterviewRecordsExpanded(isExpanded) {
  state.interviewRecordsExpanded = isExpanded;
  updateInterviewRecordsLayout();
}

function setQuestionDrawerOpen(isOpen) {
  const drawer = $("questionDrawer");
  const toggleButton = $("toggleQuestionListBtn");
  if (!drawer || !toggleButton) return;
  drawer.hidden = !isOpen;
  toggleButton.textContent = isOpen ? "收起题库" : "题库列表";
  toggleButton.setAttribute("aria-expanded", String(isOpen));
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
  refreshHrInterviewOptions();
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
  refreshHrInterviewOptions();
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
  $("hrResumeSelect").addEventListener("change", () => updateInterviewConfigSummary(selectedInterviewConfig()));
  $("hrJobSelect").addEventListener("change", () => updateInterviewConfigSummary(selectedInterviewConfig()));
  $("interviewQuestionCount").addEventListener("change", () => updateInterviewConfigSummary(selectedInterviewConfig()));
  $("practiceAnswer").addEventListener("input", () => updateAnswerMeta("practiceAnswer", "practiceAnswerMeta"));
  $("resumeForm").addEventListener("submit", (event) => runAction(() => submitResumeAnalyze(event), "正在分析简历..."));
  $("jobCollectForm").addEventListener("submit", (event) => runAction(() => submitJobCollect(event), "正在导入岗位数据..."));
  $("jobSearchForm").addEventListener("submit", (event) => runAction(() => submitJobSearch(event), "正在搜索岗位..."));
  $("clearJobSearchBtn").addEventListener("click", () => runAction(clearJobSearch, "正在重置岗位搜索..."));
  $("rebuildJobVectorBtn")?.addEventListener("click", () => runAction(rebuildJobVector, "正在重建岗位索引..."));
  $("toggleQuestionListBtn").addEventListener("click", () => {
    setQuestionDrawerOpen($("questionDrawer").hidden);
  });
  $("closeQuestionListBtn").addEventListener("click", () => {
    setQuestionDrawerOpen(false);
  });
  $("toggleInterviewRecordsBtn").addEventListener("click", () => {
    setInterviewRecordsExpanded(!state.interviewRecordsExpanded);
  });
  $("collapseInterviewRecordsBtn").addEventListener("click", () => {
    setInterviewRecordsExpanded(false);
  });
  $("interviewResult").addEventListener("click", (event) => {
    const button = event.target.closest("[data-interview-report-id]");
    if (button) {
      runAction(() => showInterviewReport(Number(button.dataset.interviewReportId)), "正在加载面试记录...");
    }
  });
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
  $("questionList").addEventListener("click", (event) => {
    const practiceButton = event.target.closest("[data-practice-id]");

    if (practiceButton) {
      const question = state.questionCache.find((item) => item.id === Number(practiceButton.dataset.practiceId));
      if (question) {
        useQuestionForPractice(question);
        setQuestionDrawerOpen(false);
      }
    }
  });
}

function boot() {
  bindTabs();
  bindActions();
  updateFilterSummary(selectedFilters());
  updatePracticeSummary();
  updateInterviewConfigSummary(selectedInterviewConfig());
  setQuestionDrawerOpen(false);
  updateInterviewRecordsLayout();
  updateAnswerMeta("practiceAnswer", "practiceAnswerMeta");
  refreshConfigStatus().catch(() => {
    $("scoringMode").textContent = "评分：状态未知";
  });
  refreshResumeHistory().catch(() => {
    $("resumeHistory").textContent = "历史记录加载失败。";
  });
  refreshJobList().catch(() => {
    $("jobList").textContent = "岗位数据加载失败。";
  });
  refreshInterviewSessions().catch(() => {
    $("interviewResult").textContent = "面试记录加载失败。";
  });
  window.setTimeout(() => refreshJobVectorStatus({ showPending: true }), 0);
  runAction(seedQuestions, "正在初始化题库...");
}

boot();
