# AI Interview Agent 项目文档

这份文档合并原来的任务目标、开发进度、发布检查清单和项目展示材料，减少后续维护时多处同步的成本。`AGENTS.md` 仍然独立保存给 Codex 读取的项目上下文。

当前对话归档交接摘要见 `docs/handoff.md`。新对话建议先读 `AGENTS.md`，再读 `docs/handoff.md`，最后按需查阅本文档。

## 当前目标

持续开发 AI Interview Agent MVP，优先完成一个可演示、可测试、可迭代的 AI 面试练习系统。

当前阶段重点：

- 保持后端接口稳定可用。
- 继续打磨前端练习和模拟面试体验。
- 提升题库质量，而不是单纯堆题量。
- 每次开发后同步更新 `AGENTS.md` 和本文档。
- 不提交 `.env`、真实 API Key、本地数据库和缓存文件。

## 当前产品范围

第一版 MVP 已包含：

- 题库初始化。
- 题库分类、难度、题型筛选。
- 问答题、单选题、多选题。
- 题目新增、编辑、删除。
- 题库练习与结构化评分反馈。
- 练习答案 SSE 流式评分进度。
- 模拟面试会话、逐题答题和最终报告。
- mock 评分和 OpenAI 兼容 LLM 评分模式。
- PDF/DOCX 简历上传分析，生成岗位推荐、技能画像、薄弱项和练习建议。
- 岗位知识库 JSONL 导入，保存公司、岗位、能力要求、技能和来源 URL。
- 本地岗位向量索引，简历分析优先检索真实 JD 进行客制化岗位推荐。
- 阿里云百炼千问 `qwen3.7-plus` 兼容配置。
- LLM 失败自动回退 mock。
- 前端顶部状态、题库列表、练习区和模拟面试区。

暂不优先做：

- 登录注册。
- 多用户权限。
- 复杂后台管理。
- 真实支付或部署。
- 过早引入复杂前端工程，除非当前静态页面明显不够用。

## 已完成内容

- GitHub 仓库已创建并连接远程：`https://github.com/WuJiaJun1020/ai-interview-agent.git`。
- 本地项目使用 Conda 环境：`ai-interview-agent`。
- 已创建一键启动脚本：`start-backend.bat`。
- 已完成 FastAPI 后端基础骨架。
- 已完成 SQLite + SQLAlchemy 数据库连接。
- 已完成题库表、模拟面试会话表和答题记录表。
- 已完成题库 CRUD 和种子题库初始化接口。
- 当前种子题库共 69 道，覆盖 Python、FastAPI、MySQL、Redis、HTTP、Git、Linux、Docker、算法、系统设计 10 个分类。
- 已支持问答题 `short_answer`、单选题 `single_choice`、多选题 `multiple_choice`。
- 已完成练习抽题、提交答案和流式评分接口。
- 已完成模拟面试创建会话、提交答案和查看报告接口。
- 已完成 mock 评分和 LLM 评分统一入口。
- 已支持 DashScope/OpenAI 兼容配置，不暴露真实 API Key。
- 已完成前端单页应用，支持题库管理、练习和模拟面试。
- 已完成前后端目录拆分：后端在 `backend/`，前端静态文件在 `frontend/`。
- 已合并本地 SQLite 数据库到 `backend/dev.db`，根目录不再保留活动 `dev.db`。
- 已完成第一轮前端模块拆分：`app.js` 作为入口，API 请求、状态、渲染和工具函数拆成独立 ES Modules。
- 已新增 PDF/DOCX 简历分析 MVP，支持上传文件、提取文本、分段展示进度、入库并输出岗位画像。
- 简历分析历史结果可复看，无需重复上传同一份简历。
- 已新增岗位知识库 MVP，支持上传已采集好的 JSONL 岗位数据，并按内容哈希去重。
- 自动公开网页采集效果不稳定，已改为使用外部采集脚本结果导入。
- 已接入 Chroma 本地持久化岗位向量库，支持重建/查看索引状态；旧本地哈希索引保留为兜底。
- 简历分析已接入岗位知识库推荐：先用 Chroma 召回 Top 8 真实 JD，再压缩候选岗位上下文，LLM 模式下在同一次简历分析调用中结合简历输出 Top 3；知识库不足或 LLM 不可用时回退规则排序/自由推荐。
- LLM 精排结果会保存并展示精排排名、匹配等级、推荐理由、能力缺口和简历优化建议。
- 已修复简历分析前端请求超时导致的 `signal is aborted without reason`：分析请求允许更长等待，失败时结果区展示错误卡片，不再停留在 pending 状态。
- 已为 OpenAI/DashScope 兼容 LLM 调用增加 `LLM_TIMEOUT_SECONDS`，默认 120 秒，超时后按现有逻辑回退 mock。
- 简历分析历史结果支持删除，会同时移除该简历文本和关联分析结果；LLM 分析等待阶段会轮播展示岗位检索、证据整理和 LLM 生成等过程提示。
- 已增强岗位推荐解释：匹配岗位会展示命中信号、JD 证据片段、推荐理由和能力缺口。
- 已清理岗位推荐中已不再展示的 `practice_plan` 字段，岗位推荐现在聚焦推荐理由、能力缺口、命中信号和 JD 证据片段。
- 岗位知识库页面已支持关键词搜索，可按公司、岗位、技能、城市、岗位描述和岗位要求筛选。
- 当前 RAG 岗位检索优先使用 Chroma，内置哈希 embedding，后续可升级为真实 embedding API。
- 已添加后端冒烟测试：`backend/tests/test_smoke.py`。
- 已维护 `README.md` 和 `AGENTS.md`。

## 当前架构

```text
ai-interview-agent/
  backend/
    app/
      api/                 # API 路由
      core/                # 配置
      data/                # 种子题库
      db/                  # 数据库连接
      models/              # SQLAlchemy 模型
      schemas/             # Pydantic Schema
      services/            # 评分、LLM、种子数据等服务
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

当前前端仍由 FastAPI 托管：

- 页面入口：`http://127.0.0.1:8000/`
- 静态资源：`/static/...`
- API 文档：`http://127.0.0.1:8000/docs`

## 下一步计划

下一步建议围绕“题库质量 + 练习体验”推进：

1. 题库结构增强：
   - 为题目增加标签能力，例如 `基础概念`、`项目经验`、`排查问题`、`系统设计`、`源码/原理`。
   - 后端题目模型、Schema、CRUD 和筛选接口同步支持标签。
   - 前端增加标签筛选，让用户能更快找到想练的题。
2. 高质量扩充题库：
   - 在现有 10 个分类基础上补充更贴近真实面试的题。
   - 优先补充 Python 并发、FastAPI 中间件、MySQL 索引失效、Redis 缓存一致性、Docker 部署排错、系统设计取舍等方向。
   - 同时补充更多单选题和多选题。
3. 练习反馈增强：
   - 评分结果增加“下一步练习建议”。
   - 根据得分、分类、难度和评分点覆盖情况提示用户继续练什么。
   - LLM 模式下继续优化提示词，让输出更稳定。
4. 前端代码结构整理：
   - 已完成第一轮 ES Module 拆分。
   - 后续继续按题库管理、练习流、模拟面试流拆分业务逻辑。
   - 暂时不引入构建工具，除非静态页面继续膨胀到难以维护。
5. 中长期计划：
   - 增加 txt/md 素材上传，支持 LLM 生成和优化简历。
   - 继续优化岗位知识库推荐质量，将当前内置哈希 embedding 升级为 DashScope/OpenAI embedding API。
   - 验证千问 3.7 Plus 真实评分质量。
   - 完善 Chroma/RAG 工作流，增加更细粒度的 chunk 策略和检索评估。
   - 添加 LangGraph 面试工作流。
   - 完善展示材料和发布检查。
   - MVP 稳定后打标签 `v0.1.0`。

## 自测与验收

后端自测命令：

```bash
conda run -n ai-interview-agent python -m pytest backend/tests
```

前端静态脚本语法检查：

```bash
node --check frontend\app.js
```

当前已验证结果：

```text
python -m pytest backend/tests --basetemp .pytest_tmp -> 6 passed
python -m pytest backend/tests --basetemp .pytest_tmp_resume_fix2 -> 6 passed
python -m pytest backend/tests --basetemp .pytest_tmp_resume_delete -> 6 passed
python -m pytest backend/tests --basetemp .pytest_tmp_chroma_final -> 6 passed
python -m pytest backend/tests --basetemp .pytest_tmp_rerank -> 7 passed
python -m pytest backend/tests --basetemp .pytest_tmp_single_llm -> 7 passed
python -m pytest backend/tests --basetemp .pytest_tmp_cleanup -> 7 passed
Chroma 岗位索引重建验证 -> 180 个岗位 / 540 个片段，backend=chroma，collection=job_posts
node --check frontend\app.js -> passed
node --check frontend\api.js -> passed
node --check frontend\render.js -> passed
node --check frontend\state.js -> passed
node --check frontend\utils.js -> passed
GET /                  -> 200
GET /static/app.js     -> 200
GET /static/api.js     -> 200
GET /static/render.js  -> 200
GET /static/styles.css -> 200
```

用户主要测试前端，正确结果包括：

- `http://127.0.0.1:8000/` 能正常打开。
- 点击“初始化题库”后题库数量正常显示。
- 分类、难度、题型筛选能正常影响题库列表和抽题。
- 问答题、单选题、多选题都能提交答案。
- 提交练习答案后先出现评分进度，再显示完整反馈。
- 新增、编辑、删除题目后，题库列表能同步变化。
- 模拟面试能按设置题数完成，并显示最终报告。
- 页面顶部能显示评分模式和 LLM 配置状态，但不暴露 API Key。
- “简历分析”Tab 可以上传 PDF/DOCX，并展示提取进度、分析进度、推荐岗位、技能画像、风险点和练习建议。
- “简历分析”Tab 会展示基于岗位知识库的匹配岗位、匹配原因、能力缺口和准备重点。
- “简历分析”Tab 在 LLM 模式下会展示岗位 Top 3 精排判断、推荐理由、风险点和简历优化建议。
- “简历分析”Tab 会展示岗位推荐的命中信号、JD 证据片段、推荐理由和能力缺口。
- “岗位知识库”Tab 可以上传 JSONL 文件导入 JD、重建岗位索引，并展示岗位数据。
- “岗位知识库”Tab 可以按关键词搜索公司、岗位、技能和 JD 文本。

## 提交前检查

- 后端自动化测试通过。
- 前端各 JS 模块 `node --check` 通过。
- 前端核心流程可以手动跑通。
- 简历 PDF/DOCX 上传分析流程可以跑通，历史结果可以复看。
- 简历分析失败或超时时，右侧结果区需要展示明确失败原因，不应一直显示“正在生成岗位画像”。
- 岗位 JSONL 导入流程可以跑通，不在应用内采集登录态或个人信息。
- 岗位索引重建和简历知识库推荐流程可以跑通。
- `http://127.0.0.1:8000/docs` 可以打开。
- `.env` 没有被 Git 跟踪。
- 真实 API Key 没有写入代码、README 或文档。
- `dev.db`、`*.sqlite`、`*.sqlite3` 没有被 Git 跟踪。
- `__pycache__`、`.pytest_cache` 等缓存没有被 Git 跟踪。
- 本次实现内容已更新到 `AGENTS.md` 和本文档。

## 项目展示材料

一句话简介：

AI Interview Agent 是一个基于 FastAPI 的 AI 模拟面试与题库练习系统，支持题库管理、分类练习、模拟面试、答案评分反馈，并预留真实 LLM、RAG 和 LangGraph 扩展能力。

简历描述：

```text
AI 模拟面试系统 | FastAPI / SQLite / SQLAlchemy / JavaScript / OpenAI API

- 设计并实现一个 AI 面试练习 MVP，支持题库管理、分类练习、模拟面试、答案评分反馈和面试报告展示。
- 使用 FastAPI 构建后端接口，基于 SQLAlchemy 和 SQLite 管理题库、面试会话和答题记录。
- 实现题库 CRUD、种子题库初始化、按分类/难度筛选、随机抽题和多轮模拟面试流程。
- 前端使用原生 HTML/CSS/JavaScript 构建单页应用，支持题目新增/编辑/删除、练习评分展示、面试进度和最终报告展示。
- 设计 mock 评分与 LLM 评分双模式，默认本地 mock 可运行，配置 OpenAI 或 DashScope API Key 后可切换 OpenAI 兼容 LLM 评分，并支持失败自动回退和结构化反馈展示。
```

项目亮点：

- 完整闭环：从题库、练习、评分到模拟面试报告都已跑通。
- 题库覆盖 10 个后端分类，支持初级、中级、高级和多种题型。
- 默认 mock 评分，不需要 API Key 也能本地演示。
- 支持 OpenAI 兼容 LLM 评分和阿里云百炼千问兼容模式。
- LLM 不可用时自动回退 mock，演示更稳定。
- 练习结果和面试报告展示评分来源、优点、问题、建议和评分点覆盖情况。
- 练习提交使用 SSE 流式进度，避免 LLM 评分期间页面静默等待。
