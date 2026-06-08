# AI Interview Agent

AI Interview Agent 是一个 AI 模拟面试与题库练习 MVP。当前版本已经可以在本地完成题库管理、题库练习、模拟面试、mock 评分和 LLM 评分配置准备。

## 当前功能

- 题库初始化：内置 Python、FastAPI、MySQL、Redis、HTTP、Git、Linux、Docker、算法、系统设计等 10 类题库，共 60 道，覆盖初级、中级、高级。
- 题库管理：在网页中新增、编辑、删除题目。
- 题库练习：按分类和难度筛选题目，选择题目练习，提交答案后查看评分、反馈、参考答案和评分点覆盖情况。
- 模拟面试：选择分类、难度和题数，逐题回答，最后查看每题得分等级、平均分、复习建议和下一步行动。
- 工作台状态：顶部展示筛选范围、当前练习题和模拟面试进度，题目以结构化卡片展示。
- 评分模式：默认使用 mock 规则评分；配置 API Key 后可以切换到 OpenAI 兼容 LLM 评分。
- 状态展示：页面顶部显示题库数量和当前评分模式。

## 技术栈

- 后端：FastAPI、SQLAlchemy、SQLite、Pydantic Settings
- 前端：FastAPI 托管的原生 HTML/CSS/JavaScript 单页应用
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
      static/              # 前端页面
      main.py
    requirements.txt
  docs/
    development-progress.md
    release-checklist.md
    task-goals.md
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

## LLM 评分配置

默认不需要 API Key，系统使用 mock 评分。

如果要启用真实 LLM 评分，在项目根目录创建 `.env`，不要提交这个文件：

```env
SCORING_MODE=llm
OPENAI_API_KEY=你的真实 key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

重启后端后，页面顶部评分状态会显示 LLM 配置情况。若 LLM 调用失败，系统会自动回退 mock 评分，避免影响本地演示。

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

## 安全注意事项

- 不要提交 `.env`。
- 不要把真实 API Key 写进代码或文档。
- 不要提交本地数据库文件，例如 `backend/dev.db`。
- 不要提交向量库文件，后续接入 RAG 时也要保持本地数据被忽略。

## 当前文档

- `AGENTS.md`：给 Codex 和开发者看的项目上下文。
- `docs/development-progress.md`：已完成功能和测试方式。
- `docs/task-goals.md`：长期任务目标和需求变更规则。
- `docs/project-showcase.md`：项目展示、简历描述和面试讲解材料。
- `docs/release-checklist.md`：提交、演示和打标签前的检查清单。

## 后续计划

- 验证真实 LLM 评分效果并优化提示词。
- 继续打磨前端交互体验。
- 接入 RAG 和向量库 Chroma。
- 引入 LangGraph 管理更完整的多轮面试流程。
- MVP 稳定后打标签 `v0.1.0`。
