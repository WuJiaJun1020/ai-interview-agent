export const $ = (id) => document.getElementById(id);

export function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function queryString(filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && String(value).trim() !== "") {
      params.set(key, value);
    }
  });
  return params.toString();
}

export function parseError(message) {
  if (message.includes("No question found")) return "没有找到符合条件的题目，请先初始化题库或调整筛选条件";
  if (message.includes("Interview session is finished")) return "本轮面试已结束，请开始新的面试";
  if (message.includes("Not Found")) return "当前后端还没有加载岗位 HR 面试接口，请重启后端后再试";
  if (message.includes("HR interview session")) return "岗位 HR 面试会话不可用，请重新开始一轮面试";
  if (message.includes("Resume not found")) return "没有找到这份简历，请重新选择已分析的简历";
  if (message.includes("Job post not found")) return "没有找到这个岗位，请重新选择岗位库中的目标岗位";
  if (message.includes("Failed to fetch")) return "无法连接后端，请确认服务已启动";
  return message;
}

export function orderedDifficulties(difficulties) {
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

export function questionTypeLabel(type) {
  if (type === "multiple_choice") return "多选题";
  return type === "single_choice" ? "单选题" : "问答题";
}

export function isChoiceType(type) {
  return type === "single_choice" || type === "multiple_choice";
}

export function scoreSourceLabel(source) {
  if (source === "llm") return { label: "LLM 评分", className: "source-llm" };
  return { label: "mock 评分", className: "source-mock" };
}

export function scoreLevel(score) {
  if (score >= 80) return { label: "表现较好", className: "level-strong" };
  if (score >= 60) return { label: "基本达标", className: "level-ok" };
  return { label: "需要加强", className: "level-weak" };
}

export function reportNextSteps(averageScore) {
  if (averageScore >= 80) {
    return ["尝试提高难度或增加题数", "回答时补充更多项目细节", "练习更强的结构化表达"];
  }
  if (averageScore >= 60) {
    return ["复盘待补充概念", "每题先用 3 点结构作答", "用项目例子支撑结论"];
  }
  return ["先复习当前分类基础概念", "参考答案后重新组织回答", "减少一次性选择过多题数"];
}
