# AI Interview Agent 项目上下文

这个文件用于记录项目当前状态、开发约定和后续计划，方便下一次 Codex 或开发者接着工作。

## 项目目标

构建一个 AI 模拟面试与题库练习系统 MVP。第一版重点是完成一个最小但完整的闭环：

- 用户选择岗位方向、分类和难度。
- 系统抽取或生成面试题。
- 用户提交答案。
- 系统给出评分、反馈和参考答案。
- 后续接入 RAG、LangChain、LangGraph 和前端页面。

## 开发节奏

采用小步开发：

- 一次只实现一个小功能。
- 后端能自动测试的部分由 Codex 自测。
- 用户主要测试前端页面和交互体验。
- 测试通过后再继续下一步。
- 已实现和待开发功能需要持续记录在 `AGENTS.md` 和 `docs/project-notes.md` 中。
- 后期需求可能改变，需要同步维护项目文档。

当前文档：

- `AGENTS.md`：给 Codex 读取的项目上下文，保持独立。
- `docs/project-notes.md`：合并后的项目文档，包含任务目标、开发进度、测试/发布检查和展示材料。
- `docs/handoff.md`：当前对话归档交接摘要，方便新对话快速接手。

## 本地环境

项目使用 Conda 环境：

```bash
conda activate ai-interview-agent
```

环境位置：

```text
C:\Users\wujiajun\anaconda3\envs\ai-interview-agent
```

后端依赖文件：

```text
backend/requirements.txt
```

已安装的核心依赖：

- FastAPI
- Uvicorn
- Pydantic Settings
- HTTPX
- SQLAlchemy
- python-multipart
- pypdf
- python-docx

## 启动方式

推荐方式：双击项目根目录下的启动脚本：

```text
start-backend.bat
```

手动启动方式：

```bash
conda activate ai-interview-agent
cd backend
uvicorn app.main:app --reload
```

启动后访问：

- `http://127.0.0.1:8000/`
- `http://127.0.0.1:8000/api/health`
- `http://127.0.0.1:8000/api/db/status`
- `http://127.0.0.1:8000/docs`

## 已完成内容

- GitHub 仓库已创建并连接远程：`https://github.com/WuJiaJun1020/ai-interview-agent.git`
- 本地项目在 `main` 分支，远程为 `origin/main`。
- 已创建 FastAPI 后端基础骨架。
- 已创建根接口：`GET /`。
- 已创建健康检查接口：`GET /api/health`。
- 已创建 Conda 环境：`ai-interview-agent`。
- 已安装当前后端依赖。
- 已创建一键启动脚本：`start-backend.bat`。
- 已添加 SQLite + SQLAlchemy 基础连接。
- 已添加初始题目表模型：`questions`。
- 已创建数据库状态接口：`GET /api/db/status`。
- 已创建题目请求/响应 Schema。
- 已创建题库接口：`POST /api/questions` 和 `GET /api/questions`。
- 已补齐题库 CRUD 基础接口：详情、修改、删除。
- 题目列表接口支持通过 `category` 和 `difficulty` 查询参数筛选。
- 已添加并扩充种子题库数据：Python、FastAPI、MySQL、Redis、HTTP、Git、Linux、Docker、算法、系统设计。
- 当前种子题库共 69 道，10 个分类，每类初级/中级/高级各 2 道，并额外包含 6 道单选题和 3 道多选题。
- 题库模型支持问答题 `short_answer`、单选题 `single_choice` 和多选题 `multiple_choice`。
- 练习提交新增 SSE 流式接口 `POST /api/practice/answer/stream`，前端会立即显示评分进度。
- 已添加 `POST /api/questions/seed` 初始化题库接口，重复调用不会重复插入。
- 已添加练习接口：`GET /api/practice/question` 和 `POST /api/practice/answer`。
- 练习答案评分目前是 mock 规则评分，不调用真实 LLM。
- 已移除重复的题库模拟面试功能，题库相关练习统一保留在“题库练习”页面。
- 已新增岗位 HR 面试 MVP：可选择已分析简历和岗位知识库中的目标岗位，让 AI/Mock 面试官根据“岗位 JD + 简历内容”生成面试问题。
- 岗位 HR 面试数据已落 SQLite 表：`hr_interview_sessions` 和 `hr_interview_answers`。
- 已新增岗位 HR 面试接口：`POST /api/interview/hr-sessions`、`POST /api/interview/hr-sessions/{session_id}/answer`、`GET /api/interview/hr-sessions/{session_id}/report`。
- 已新增岗位 HR 面试 SSE 流式接口：`POST /api/interview/hr-sessions/stream` 和 `POST /api/interview/hr-sessions/{session_id}/answer/stream`。
- 岗位 HR 面试在 `SCORING_MODE=llm` 且配置 Key 后会尝试真实 LLM 生成问题和反馈；失败或 mock 模式下会自动回退本地规则。
- 已添加 FastAPI 托管的前端单页界面：`GET /`。
- 前端支持题库初始化、题库练习、岗位 HR 面试和报告展示。
- 前端已添加题库列表视图，可按筛选条件查看题目并点击“练这题”。
- 前端已添加新增题目表单，保存后会刷新列表并选中新题练习。
- 前端已添加题目编辑和删除入口。
- 前端题库列表已有当前练习题和编辑题目的高亮状态。
- 练习评分结果已改为结构化展示。
- 模拟面试页面已有进度条、逐题记录卡片和最终报告卡片。
- 岗位 HR 面试报告已增强：当前平均分、阶段判断、每题分数等级、用户回答、岗位匹配反馈、最终报告指标和下一步行动。
- 前端已改为左侧固定导航布局，产品名位于界面左上角；各模块状态收回对应页面内展示，不再跨页面固定显示题库练习信息。
- 练习题和面试题已改为结构化题目卡片，展示编号、分类、难度和评分点。
- 练习和面试答题框已添加字数提示。
- 题库空状态已改为可读提示。
- 岗位 HR 面试支持选择题数，并展示本轮简历、岗位和题数配置。
- 模拟面试页已移除重复的题库模拟功能，仅保留岗位 HR 面试；岗位 HR 面试模式支持选择历史简历和目标岗位后开始面试。
- 岗位 HR 面试前端已支持问题生成、回答反馈和下一题生成的流式展示；最后一题提交后左侧会保留本轮问题、用户回答和面试官反馈，不再直接替换成结束提示。
- 模拟面试页已改为对话式面试舱：中间为 AI/用户聊天气泡和底部输入框，右侧为面试进度、面试信息和紧凑面试记录。
- 前端分类下拉和新增题目的分类候选项会根据题库自动生成。
- 前端难度下拉和新增题目的难度候选项会根据题库自动生成。
- 前端题库状态会显示全库题量、分类数和难度数。
- 已准备真实 LLM 评分接入：`SCORING_MODE=mock|llm`，默认 mock；配置 OpenAI API Key 或 DashScope API Key 后可切换到 LLM 评分。
- 已支持阿里云百炼千问兼容模式：本地 `.env` 可配置 `DASHSCOPE_API_KEY`、`OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`、`OPENAI_MODEL=qwen3.7-plus`、`LLM_ENABLE_THINKING=true`。
- 评分结果已扩展为结构化输出：`source`、`strengths`、`weaknesses`、`suggestions`、评分点覆盖和参考答案。
- 前端练习反馈和模拟面试记录会展示评分来源、优点、问题和建议。
- 前端在作答区域展示选择题选项：单选题用单选按钮，多选题用复选框。
- LLM 评分失败会自动回退 mock，避免影响本地演示。
- 已添加 `GET /api/config/status`，前端左侧导航底部会显示当前评分模式和 LLM 配置状态，不暴露 API Key。
- 已添加 `.env.example`。
- 已更新 `.gitignore`，忽略本地数据库文件，例如 `dev.db`。
- 已完善 `README.md`，包含功能、启动、LLM 配置、安全注意事项和后续计划。
- 已将任务目标、开发进度、发布检查和项目展示材料合并到 `docs/project-notes.md`。
- 已添加后端自动化冒烟测试：`backend/tests/test_smoke.py`。
- 已添加测试依赖 `pytest`。
- 已将 FastAPI 启动初始化改为 lifespan。
- 已完成第一轮项目结构优化：前端静态文件已从 `backend/app/static/` 移到顶层 `frontend/`，后端继续由 FastAPI 托管页面。
- 已合并本地 SQLite 数据库到 `backend/dev.db`，根目录不再保留活动 `dev.db`。
- 已完成第二轮前端结构优化：`frontend/app.js` 已拆分为 ES Modules，包含 API 请求、状态、渲染和工具函数模块。
- 已新增 PDF/DOCX 简历分析 MVP：上传文件、提取文本、保存简历记录、生成岗位画像和练习建议。
- 简历分析前端会分开显示“文字提取”和“岗位分析”进度，降低等待焦虑。
- 简历分析历史结果已保存，可在“历史结果”里直接查看，无需重复上传同一份简历。
- 简历分析默认使用 mock 规则；`SCORING_MODE=llm` 且配置 Key 后会尝试 LLM 分析，失败回退 mock。
- 已修复简历分析前端 8 秒超时导致的 `signal is aborted without reason`：分析请求改为更长超时，失败时右侧结果区会显示错误卡片，不再停留在“文字提取完成，正在生成岗位画像”。
- 已为 LLM 调用增加 `LLM_TIMEOUT_SECONDS` 配置，默认 120 秒；简历分析和练习评分的真实 LLM 请求超时后会按现有逻辑回退 mock。
- 简历分析历史结果支持删除，会同时移除该简历文本和关联分析结果；LLM 分析等待阶段会轮播展示岗位检索、证据整理和 LLM 生成等过程提示。
- 已新增岗位知识库 MVP：上传已采集好的 JSONL 岗位数据，保存岗位名称、公司、技能、要求和来源 URL。
- 自动公开网页采集效果不稳定，已退场；当前采用用户自有采集脚本产出的 JSONL 导入。
- 岗位导入按内容哈希去重，重复导入同一份 JSONL 不会重复插入。
- 已接入 Chroma 本地持久化岗位向量库：`backend/vector_store/chroma/`，collection 为 `job_posts`，目录已加入 `.gitignore`。
- Chroma 使用项目内置哈希 embedding 函数，避免本地首次运行时额外下载模型；旧的 `backend/vector_store/job_index.json` 本地哈希索引保留为兜底。
- 简历分析已接入岗位知识库推荐：先用 Chroma 召回 Top 8 真实 JD，再压缩候选岗位上下文，LLM 模式下在同一次简历分析调用中结合简历输出 Top 3；知识库不足或 LLM 不可用时回退规则排序/自由推荐。
- LLM 精排结果会保存并展示精排排名、匹配等级、推荐理由、能力缺口和简历优化建议。
- 已增强岗位知识库推荐解释：每个匹配岗位会返回命中信号、JD 证据片段、推荐理由和能力缺口。
- 已清理岗位推荐中已不再展示的 `practice_plan` 字段，岗位推荐现在聚焦推荐理由、能力缺口、命中信号和 JD 证据片段。
- 岗位知识库页面已支持关键词搜索，可按岗位名、公司、技能、城市、岗位描述和岗位要求筛选。
- 当前 RAG 岗位检索优先使用 Chroma；如果 `chromadb` 不可用或查询失败，会自动回退本地哈希词袋索引，避免简历分析不可用。

## 已验证内容

使用 Conda 环境测试通过：

```text
GET /api/health     -> 200 {"status": "ok"}
GET /api/db/status  -> 200 {"status": "ok"}
python -m pytest backend/tests --basetemp .pytest_tmp -> 6 passed
node --check frontend\app.js -> passed
node --check frontend\api.js -> passed
node --check frontend\render.js -> passed
node --check frontend\state.js -> passed
node --check frontend\utils.js -> passed
node --check frontend\app.js -> passed (20260609-layout-1)
node --check frontend\api.js -> passed (20260609-layout-1)
node --check frontend\render.js -> passed (20260609-layout-1)
node --check frontend\state.js -> passed (20260609-layout-1)
node --check frontend\utils.js -> passed (20260609-layout-1)
Browser 验证新版工作台布局 -> 左侧导航固定；题库/面试/简历/岗位页只展示自身内容；桌面视口无整页滚动，长内容在模块内滚动
node --check frontend\app.js -> passed (20260609-chat-1)
node --check frontend\api.js -> passed (20260609-chat-1)
node --check frontend\render.js -> passed (20260609-chat-1)
node --check frontend\state.js -> passed (20260609-chat-1)
node --check frontend\utils.js -> passed (20260609-chat-1)
Browser 验证模拟面试对话式界面 -> 中间聊天流、底部输入框、右侧进度/信息/记录正常；旧问题卡片样式已从面试主区移除
python -m pytest backend/tests --basetemp .pytest_tmp_resume_fix2 -> 6 passed
python -m pytest backend/tests --basetemp .pytest_tmp_resume_delete -> 6 passed
python -m pytest backend/tests --basetemp .pytest_tmp_chroma_final -> 6 passed
python -m pytest backend/tests --basetemp .pytest_tmp_rerank -> 7 passed
python -m pytest backend/tests --basetemp .pytest_tmp_single_llm -> 7 passed
python -m pytest backend/tests --basetemp .pytest_tmp_cleanup -> 7 passed
conda run -n ai-interview-agent python -m pytest backend\tests --basetemp .pytest_tmp_hr_interview -> 8 passed
conda run -n ai-interview-agent python -m pytest backend\tests --basetemp .pytest_tmp_hr_stream -> 9 passed
Browser 验证岗位 HR 面试 1 题流程 -> 问题生成可显示，提交后左侧保留最终反馈，右侧报告可查看
Chroma 岗位索引重建验证 -> 180 个岗位 / 540 个片段，backend=chroma，collection=job_posts
DOCX 简历上传接口验证 -> upload 201，analyze 201，匹配 6 个岗位
GET /                  -> 200
GET /static/app.js     -> 200
GET /static/api.js     -> 200
GET /static/render.js  -> 200
GET /static/styles.css -> 200
```

用户已确认 `http://127.0.0.1:8000/docs` 可以打开并看到 FastAPI Swagger UI。
用户已确认前后端目录拆分后，`http://127.0.0.1:8000/` 页面测试没有大问题。

## 当前文件结构概览

```text
ai-interview-agent/
  backend/
    app/
      api/
        config_status.py
        db_status.py
        health.py
        interview.py
        jobs.py
        practice.py
        questions.py
        resumes.py
      core/
        config.py
      data/
        seed_questions.json
      db/
        session.py
      models/
        interview.py
        job.py
        question.py
        resume.py
      schemas/
        interview.py
        job.py
        practice.py
        question.py
        resume.py
      services/
        llm_scoring.py
        hr_interview.py
        job_importer.py
        resume_analysis.py
        resume_text.py
        scoring.py
        scoring_service.py
        seed_questions.py
      main.py
    tests/
      test_smoke.py
    requirements.txt
  frontend/
    index.html
    app.js
    api.js
    render.js
    state.js
    styles.css
    utils.js
  docs/
    project-notes.md
  .env.example
  .gitignore
  AGENTS.md
  README.md
  start-backend.bat
```

## 下一步计划

下一步建议围绕“题库质量 + 练习体验”推进，而不是单纯堆题量：

1. 题库结构增强：
   - 为题目增加标签能力，例如 `基础概念`、`项目经验`、`排查问题`、`系统设计`、`源码/原理`。
   - 后端题目模型、Schema、CRUD 和筛选接口同步支持标签。
   - 前端增加标签筛选，让用户能更快找到想练的题。
2. 高质量扩充题库：
   - 在现有 10 个分类基础上补充更贴近真实面试的题。
   - 优先补充 Python 并发、FastAPI 中间件、MySQL 索引失效、Redis 缓存一致性、Docker 部署排错、系统设计取舍等方向。
   - 同时补充单选题和多选题，避免题库继续偏向问答题。
3. 练习反馈增强：
   - 评分结果增加“下一步练习建议”，根据得分、分类、难度和评分点覆盖情况提示用户继续练什么。
   - LLM 模式下优化提示词，让输出更稳定、更像面试官反馈。
4. 前端代码结构继续整理：
   - 已完成第一轮拆分：API 请求、状态管理、渲染组件和工具函数已拆成独立 ES Modules。
   - 后续继续按功能边界拆分练习流、岗位 HR 面试流和题库管理逻辑。
   - 当前 UI 已从顶部 tab 堆叠布局改为左侧导航 + 右侧工作区，后续新增页面应沿用“页面内状态、模块内滚动”的布局约定。
5. 后续中长期计划：
   - 为简历制作/优化增加 txt/md 素材上传和 LLM 生成简历功能。
   - 继续优化岗位知识库推荐质量，后续可将当前哈希 embedding 升级为 DashScope/OpenAI embedding API。
   - 验证千问 3.7 Plus 真实评分质量。
   - 完善 Chroma/RAG 工作流，增加更细粒度的 chunk 策略、重排和检索评估。
   - 添加 LangGraph 面试工作流。
   - 完善 README、展示材料和发布检查。
   - MVP 稳定后打标签 `v0.1.0`。

## 注意事项

- 不要提交 `.env`、真实 API Key、本地数据库文件或向量库文件。
- API Key 只应由用户自己保存在本地 `.env` 中。
- 用户曾提供千问 API Key，已写入本地忽略文件 `.env`，禁止提交、打印或写入文档。
- 当前默认数据库文件为 `backend/dev.db`，应保持被 Git 忽略。
- 开发阶段本地验证数据不重要，默认不额外保留数据库备份。
- 简历分析上传的是本地 PDF/DOCX，当前保存提取出的文本和分析结果到本地 SQLite；数据库不提交到 Git。
- 真实 LLM 调用默认 `LLM_TIMEOUT_SECONDS=120`；如果网络或模型响应慢，后端会超时并由业务逻辑回退 mock，前端也会展示可读错误，不应让结果区一直处于 pending。
- 岗位知识库当前通过 JSONL 导入，不在应用内做网页爬取；后续如恢复采集，必须尊重 robots.txt、限速和来源记录，不要绕过登录、验证码或平台反爬。
- 后端可自动测试的内容，Codex 先自测通过再交付。
- 用户主要负责测试前端页面和交互。
- 用户希望开发速度比早期更快一点，但仍要保证质量。
- 用户希望文档使用中文，方便自己阅读。
- 文档数量已收敛：除 `README.md` 和独立的 `AGENTS.md` 外，`docs/` 下主要维护 `project-notes.md`。
- 当前归档交接信息已写入 `docs/handoff.md`；新对话应先读 `AGENTS.md`，再读 `docs/handoff.md`。

## 当前架构约定

- 后端代码放在 `backend/`，FastAPI 应用入口为 `backend/app/main.py`。
- 前端静态页面放在顶层 `frontend/`，当前包括 `index.html`、`styles.css` 和若干原生 ES Module 脚本。
- 当前阶段仍由 FastAPI 托管前端，访问 `http://127.0.0.1:8000/` 会返回 `frontend/index.html`。
- 静态资源路径保持为 `/static/...`，实际文件来源是顶层 `frontend/` 目录。
- 后续如果原生前端继续变复杂，再考虑升级为独立前端工程，例如 Vite 或 Next.js；在此之前保持轻量结构，避免过早引入复杂构建链。
