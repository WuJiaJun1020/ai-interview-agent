# 当前交接摘要

更新时间：2026-06-09

这份文档用于把当前对话的工作状态交给下一轮对话或开发者。长期项目背景仍以根目录 `AGENTS.md` 和 `docs/project-notes.md` 为准。

## 当前状态

- 项目是 AI 模拟面试与题库练习 MVP，后端 FastAPI，前端原生 HTML/CSS/JavaScript ES Modules。
- 前端由 FastAPI 托管，访问 `http://127.0.0.1:8000/`。
- 当前默认数据库是 `backend/dev.db`，不提交 Git。
- 本地向量库目录是 `backend/vector_store/`，不提交 Git。
- 用户本地 `.env` 可能包含真实 DashScope/OpenAI API Key，禁止打印、提交或写入文档。
- 当前工作区有较多未跟踪文件，它们主要是本轮新增的简历分析、岗位知识库和前端拆分模块，不是无用文件。

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
- 模拟面试：创建会话、逐题答题、最终报告。
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
20260609-rag-7
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
node --check frontend\app.js -> passed
node --check frontend\api.js -> passed
node --check frontend\render.js -> passed
node --check frontend\state.js -> passed
node --check frontend\utils.js -> passed
```

浏览器验证过前端加载：

```text
/static/app.js?v=20260609-rag-7
/static/styles.css?v=20260609-rag-7
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
