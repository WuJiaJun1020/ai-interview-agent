# AI Interview Agent

AI Interview Agent 是一个 AI 模拟面试与题库练习 MVP。当前版本已经可以在本地完成题库管理、题库练习、模拟面试、mock 评分和 LLM 评分配置准备。

## 当前功能

- 题库初始化：内置 Python、FastAPI、MySQL、Redis、HTTP、Git、Linux、Docker、算法、系统设计等 10 类题库，共 69 道，覆盖初级、中级、高级，并包含问答题、单选题和多选题。
- 题库管理：在网页中新增、编辑、删除题目。
- 题库练习：按分类、难度和题型练习题目，支持问答题、单选题和多选题；提交答案后会先显示评分进度，再展示评分来源、优点、问题、建议、参考答案和评分点覆盖情况。
- 模拟面试：选择分类、难度和题数，逐题回答，最后查看每题评分来源、得分等级、平均分、复习建议和下一步行动。
- 简历分析：上传 PDF/DOCX 简历，系统分阶段提取文本、结合岗位知识库生成推荐岗位、技能画像、薄弱项和练习建议，并保存历史结果。
- 岗位知识库：上传已采集好的 JSONL 岗位数据，保存岗位能力要求、技能和来源链接，并按内容哈希去重。
- 岗位推荐索引：支持 Chroma 本地持久化岗位向量库，简历分析会先召回 Top 8 真实 JD、压缩候选上下文，再在同一次 LLM 分析里结合简历输出 Top 3；知识库不足、Chroma 不可用或 LLM 不可用时自动回退规则推荐/自由推荐。
- 工作台状态：顶部展示筛选范围、当前练习题和模拟面试进度，题目以结构化卡片展示。
- 评分模式：默认使用 mock 规则评分；配置 API Key 后可以切换到 OpenAI 兼容 LLM 评分。
- 状态展示：页面顶部显示题库数量和当前评分模式。

## 技术栈

- 后端：FastAPI、SQLAlchemy、SQLite、Pydantic Settings、pypdf、python-docx、python-multipart、Chroma
- 前端：FastAPI 托管的原生 HTML/CSS/JavaScript 单页应用，使用 ES Modules 拆分代码
- 评分：mock 规则评分，预留 OpenAI 兼容 Chat Completions 评分
- 环境：Conda

## 项目结构

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
      services/            # 评分、种子数据等服务
      main.py
    requirements.txt
  frontend/                # 前端静态页面
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
  AGENTS.md
  start-backend.bat
```

## 本地启动

推荐方式：双击项目根目录下的：

```text
start-backend.bat
```

手动方式：

```bash
conda activate ai-interview-agent
cd backend
uvicorn app.main:app --reload
```

打开页面：

- 前端页面：http://127.0.0.1:8000/
- API 文档：http://127.0.0.1:8000/docs

## 第一次使用

1. 打开 `http://127.0.0.1:8000/`。
2. 点击“初始化题库”。
3. 在“题库练习”中选择分类，点击“抽一道题”或在题库列表点“练这题”。
4. 输入答案并提交，查看右侧评分反馈。
5. 切到“模拟面试”，选择题数并开始面试。
6. 切到“简历分析”，上传 PDF 或 DOCX 简历查看岗位和练习建议，之后可从历史结果直接复看。
7. 切到“岗位知识库”，上传 JSONL 岗位数据文件导入岗位知识库。

## LLM 评分配置

默认不需要 API Key，系统使用 mock 评分。

如果要启用真实 LLM 评分，在项目根目录创建 `.env`，不要提交这个文件。

OpenAI 官方接口示例：

```env
SCORING_MODE=llm
OPENAI_API_KEY=你的真实 key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
LLM_ENABLE_THINKING=false
LLM_TIMEOUT_SECONDS=120
```

阿里云百炼千问兼容模式示例：

```env
SCORING_MODE=llm
DASHSCOPE_API_KEY=你的真实 key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen3.7-plus
LLM_ENABLE_THINKING=true
LLM_TIMEOUT_SECONDS=120
```

重启后端后，页面顶部评分状态会显示 LLM 配置情况。若 LLM 调用失败或超过 `LLM_TIMEOUT_SECONDS`，系统会自动回退 mock，避免影响本地演示。

## 后端自测

Codex 开发过程中主要用 FastAPI TestClient 自动验证后端。运行命令：

```bash
conda run -n ai-interview-agent python -m pytest backend/tests
```

你也可以在浏览器打开：

```text
http://127.0.0.1:8000/docs
```

常用接口：

- `GET /api/health`
- `GET /api/config/status`
- `POST /api/questions/seed`
- `GET /api/questions`
- `POST /api/practice/answer`
- `POST /api/interview/sessions`
- `POST /api/interview/sessions/{session_id}/answer`
- `GET /api/interview/sessions/{session_id}/report`
- `POST /api/resumes/analyze`
- `POST /api/jobs/import-jsonl`
- `GET /api/jobs`
- `GET /api/jobs/vector-index/status`
- `POST /api/jobs/vector-index/rebuild`

## 安全注意事项

- 不要提交 `.env`。
- 不要把真实 API Key 写进代码或文档。
- 不要提交本地数据库文件，例如 `backend/dev.db`。
- 不要提交向量库文件，当前本地岗位索引目录 `backend/vector_store/` 已被 Git 忽略。

## 当前文档

- `AGENTS.md`：给 Codex 和开发者看的项目上下文。
- `docs/project-notes.md`：合并后的项目文档，包含任务目标、开发进度、测试/发布检查和展示材料。

## 后续计划

- 增加题目标签能力和标签筛选。
- 增加 txt/md 素材上传，支持 LLM 生成和优化简历。
- 继续优化岗位知识库推荐质量，后续可将当前哈希 embedding 升级为 DashScope/OpenAI embedding API。
- 高质量扩充题库，补充更真实的工程题、排错题、设计题、单选题和多选题。
- 增强练习反馈，增加下一步练习建议。
- 继续按题库管理、练习流、模拟面试流拆分前端业务逻辑。
- 完善 Chroma/RAG 工作流，增加更细粒度的 chunk 策略和检索评估。
- 引入 LangGraph 管理更完整的多轮面试流程。
- MVP 稳定后打标签 `v0.1.0`。
