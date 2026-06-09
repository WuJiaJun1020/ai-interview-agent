# 当前交接摘要

更新时间：2026-06-09

这份文档用于把当前对话的工作状态交给下一轮对话或开发者。长期项目背景仍以根目录 `AGENTS.md` 和 `docs/project-notes.md` 为准。

## 当前状态

- 项目是 AI 模拟面试与题库练习 MVP，后端 FastAPI，前端原生 HTML/CSS/JavaScript ES Modules。
- 前端由 FastAPI 托管，访问 `http://127.0.0.1:8000/`。
- 当前默认数据库是 `backend/dev.db`，不提交 Git。
- 本地向量库目录是 `backend/vector_store/`，不提交 Git。
- 用户本地 `.env` 可能包含真实 DashScope/OpenAI API Key，禁止打印、提交或写入文档。
- 当前最新新增功能是岗位 HR 面试：选择已分析简历和岗位库岗位后，根据“岗位 JD + 简历内容”进行模拟 HR/一面问答。

## 启动方式

推荐双击项目根目录：

```text
start-backend.bat
```

手动启动：

```bash
conda activate ai-interview-agent
cd backend
uvicorn app.main:app --reload
```

常用地址：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/api/health`

## 关键功能

- 题库管理：初始化、列表、筛选、新增、编辑、删除。
- 题库练习：抽题、提交答案、SSE 评分进度、mock/LLM 双模式评分。
- 模拟面试：仅保留岗位 HR 面试，创建会话、逐题答题、最终报告。
- 岗位 HR 面试：基于已分析简历和岗位知识库岗位创建会话、逐题答题、生成岗位匹配反馈和报告。
- 简历分析：上传 PDF/DOCX，提取文本，保存历史，删除历史结果。
- 岗位知识库：导入用户外部脚本采集好的 JSONL，按内容哈希去重。
- 岗位向量索引：Chroma 本地持久化，旧本地哈希索引作为兜底。

## 当前简历 RAG 流程

当前正确流程是一次 LLM 分析里完成岗位推荐判断：

```text
上传 PDF/DOCX
-> 提取简历文本
-> Chroma 召回 Top 8 真实 JD
-> 压缩候选岗位上下文
-> 一次 LLM 调用：结合简历 + Top 8 JD 输出简历画像和 Top 3 岗位
-> 保存分析结果与岗位推荐历史
```

关键文件：

- `backend/app/api/resumes.py`
- `backend/app/services/resume_text.py`
- `backend/app/services/resume_analysis.py`
- `backend/app/services/job_vector_store.py`
- `frontend/render.js`
- `frontend/api.js`
- `frontend/app.js`

注意：

- 不要恢复成“两次 LLM 调用”：先独立 rerank、再简历分析。用户已明确否定该方案。
- `LLM_TIMEOUT_SECONDS` 默认已改为 120 秒。
- 前端简历分析请求超时为 240 秒。
- LLM 失败时会回退 mock 分析。
- `practice_plan` 已从岗位推荐结果中清理，前端不再展示“推荐练习方向”。

## 当前岗位 HR 面试流程

当前模拟面试页只保留岗位 HR 面试，题库相关练习统一在“题库练习”页完成：

```text
打开“模拟面试”
-> 选择一份已分析简历
-> 选择岗位知识库中的目标岗位
-> 创建 HR 面试会话
-> 根据简历正文 + 岗位 JD 流式生成当前问题
-> 用户回答
-> 根据岗位匹配度、项目证据、量化结果和表达结构流式评分反馈
-> 继续流式生成下一题，直到本轮题数结束
-> 最后一题结束后，左侧保留本轮问题、用户回答和面试官反馈
-> 查看报告
```

关键接口：

- `POST /api/interview/hr-sessions`
- `POST /api/interview/hr-sessions/stream`
- `POST /api/interview/hr-sessions/{session_id}/answer`
- `POST /api/interview/hr-sessions/{session_id}/answer/stream`
- `GET /api/interview/hr-sessions/{session_id}/report`

关键文件：

- `backend/app/services/hr_interview.py`
- `backend/app/api/interview.py`
- `backend/app/models/interview.py`
- `backend/app/schemas/interview.py`
- `frontend/app.js`
- `frontend/api.js`
- `frontend/render.js`

注意：

- 该功能需要先有简历历史和岗位库数据；否则前端下拉框会提示先上传/导入。
- `SCORING_MODE=llm` 且配置 Key 时会尝试真实 LLM 生成问题和反馈；失败自动回退 mock。
- 岗位 HR 面试没有固定参考答案，右侧记录会提示以岗位匹配反馈为准。
- 前端优先使用 SSE 流式接口；非流式接口保留为兼容路径和后端测试入口。

## 当前简历分析布局

用户已要求并已实现：

- 最上方展示“总体反馈”。
- 顶部画像区只保留 4 块：
  - 推荐岗位
  - 识别技能
  - 简历亮点
  - 风险与补强
- 不再展示顶部“练习建议”和“面试重点”。
- 岗位推荐卡不再展示“推荐练习方向”。
- LLM 精排信息压缩成一行标签，例如 `LLM 精排：Top 1 · 可冲刺 · 45 分`。
- 岗位分析合并为 2 块：
  - 推荐理由
  - 能力缺口

前端缓存版本当前为：

```text
20260609-chat-1
```

## 最近清理内容

- 删除旧文件 `backend/app/services/pdf_resume.py`。
- 移除岗位推荐结果中已不再使用的 `practice_plan` 字段和生成逻辑。
- 删除 `.pytest_tmp*` 测试临时目录和 `backend/app/**/__pycache__`。
- `.gitignore` 已改为忽略 `.pytest_tmp*/`。
- 文档已同步移除旧的“推荐练习方向”描述。

## 已验证

最近一次验证通过：

```text
conda run -n ai-interview-agent python -m pytest backend\tests --basetemp .pytest_tmp_cleanup -> 7 passed
conda run -n ai-interview-agent python -m pytest backend\tests --basetemp .pytest_tmp_hr_interview -> 8 passed
conda run -n ai-interview-agent python -m pytest backend\tests --basetemp .pytest_tmp_hr_stream -> 9 passed
Browser 验证岗位 HR 面试 1 题流程 -> 左侧流式展示提问/反馈，最终轮保留本轮反馈，右侧最终报告正常
node --check frontend\app.js -> passed
node --check frontend\api.js -> passed
node --check frontend\render.js -> passed
node --check frontend\state.js -> passed
node --check frontend\utils.js -> passed
```

浏览器验证过前端加载：

```text
/static/app.js?v=20260609-chat-1
/static/styles.css?v=20260609-chat-1
```

控制台无错误。

## 下一步建议

优先级建议：

1. 继续拆分前端业务逻辑，尤其是 `frontend/app.js` 中的题库、简历、岗位知识库流程。
2. 优化简历分析结果的可读性，例如岗位 Top 3 的横向比较、低分岗位的解释。
3. 增加题目标签能力和标签筛选。
4. 将当前内置哈希 embedding 升级为真实 embedding API，例如 DashScope/OpenAI embedding。
5. 为简历制作/优化增加 txt/md 素材上传和 LLM 生成简历功能。

## 交接注意事项

- 不要提交 `.env`、真实 API Key、`backend/dev.db`、`backend/vector_store/`。
- 不要恢复自动网页采集 JD；当前路线是导入用户外部脚本生成的 JSONL。
- 用户偏好中文文档和快节奏小步开发。
- 用户主要测试前端，后端可自动验证的部分由 Codex 先跑测试。
- 开发阶段本地验证数据不重要，默认不额外备份数据库。
