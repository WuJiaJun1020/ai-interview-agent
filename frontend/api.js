import { queryString } from "./utils.js?v=20260610-readme-shots-1";

export async function request(path, options = {}) {
  const { timeoutMs = 8000, ...fetchOptions } = options;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  let response;
  try {
    response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...fetchOptions,
      signal: controller.signal,
    });
  } catch (error) {
    if (error.name === "AbortError" || String(error.message || "").includes("aborted")) {
      throw new Error(`请求超时，已等待 ${Math.round(timeoutMs / 1000)} 秒，请稍后重试`);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  if (response.status === 204) return null;
  return response.json();
}

export function getConfigStatus() {
  return request("/api/config/status");
}

export function listQuestions(filters = {}) {
  const qs = queryString(filters);
  return request(`/api/questions${qs ? `?${qs}` : ""}`);
}

export function seedQuestionBank() {
  return request("/api/questions/seed", { method: "POST" });
}

export function getPracticeQuestion(filters = {}) {
  const qs = queryString(filters);
  return request(`/api/practice/question${qs ? `?${qs}` : ""}`);
}

export function startHrInterviewStream(payload) {
  return fetchSse("/api/interview/hr-sessions/stream", {
    body: JSON.stringify(payload),
    timeoutMs: 300000,
  });
}

export function submitHrInterviewAnswerStream(sessionId, answer) {
  return fetchSse(`/api/interview/hr-sessions/${sessionId}/answer/stream`, {
    body: JSON.stringify({ answer }),
    timeoutMs: 360000,
  });
}

export function getHrInterviewReport(sessionId) {
  return request(`/api/interview/hr-sessions/${sessionId}/report`);
}

export function listHrInterviewSessions() {
  return request("/api/interview/hr-sessions");
}

async function fetchSse(path, options = {}) {
  const { timeoutMs = 300000, body } = options;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      signal: controller.signal,
    });
    if (!response.ok || !response.body) {
      const message = await response.text();
      throw new Error(message || `Request failed: ${response.status}`);
    }
    return response;
  } catch (error) {
    if (error.name === "AbortError" || String(error.message || "").includes("aborted")) {
      throw new Error(`请求超时，已等待 ${Math.round(timeoutMs / 1000)} 秒，请稍后重试`);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function uploadResumeDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/resumes/upload", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json();
}

export function analyzeUploadedResume(resumeId) {
  return request(`/api/resumes/${resumeId}/analyze`, { method: "POST", timeoutMs: 240000 });
}

export function listResumeHistory() {
  return request("/api/resumes");
}

export function getResumeResult(resumeId) {
  return request(`/api/resumes/${resumeId}`);
}

export function deleteResumeHistoryRequest(resumeId) {
  return request(`/api/resumes/${resumeId}`, { method: "DELETE" });
}

export async function importJobsJsonl(file) {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch("/api/jobs/import-jsonl", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json();
}

export function listJobs(filters = {}) {
  const qs = queryString(filters);
  return request(`/api/jobs${qs ? `?${qs}` : ""}`);
}

export function getJobVectorStatus() {
  return request("/api/jobs/vector-index/status");
}

export function rebuildJobVectorIndex() {
  return request("/api/jobs/vector-index/rebuild", { method: "POST" });
}
