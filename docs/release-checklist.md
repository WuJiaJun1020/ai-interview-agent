# AI Interview Agent 发布检查清单

这个文件用于每次准备提交、打标签或演示前检查项目状态。

## 提交前检查

- 确认后端自动化测试通过：

```bash
conda run -n ai-interview-agent pytest backend/tests
```

- 确认前端可以启动并手动跑通核心流程：

```text
http://127.0.0.1:8000/
```

- 确认 API 文档可以打开：

```text
http://127.0.0.1:8000/docs
```

- 确认 `.env` 没有被 Git 跟踪。
- 确认真实 API Key 没有写入代码、README 或文档。
- 确认 `dev.db`、`*.sqlite`、`*.sqlite3` 没有被 Git 跟踪。
- 确认 `__pycache__`、`.pytest_cache` 等缓存文件没有被 Git 跟踪。
- 确认本次实现内容已更新到：
  - `AGENTS.md`
  - `docs/task-goals.md`
  - `docs/development-progress.md`
  - 必要时更新 `docs/project-showcase.md`

## 当前 MVP 验收标准

- 题库可以初始化，重复初始化不会重复插入。
- 题库列表可以按分类和难度筛选。
- 用户可以新增、编辑、删除题目。
- 用户可以选择指定题目练习并提交答案。
- 练习结果包含分数、反馈、评分点覆盖情况和参考答案。
- 用户可以设置模拟面试题数并完成整轮面试。
- 模拟面试结束后可以查看平均分和复习建议。
- 前端顶部能展示题库数量和评分模式。
- 后端配置状态接口不泄露 API Key。

## 版本建议

当以上检查均通过，并且 README、演示材料和任务文档都已同步后，可以考虑：

- 提交版本：`feat: build ai interview agent mvp`
- 稳定后打标签：`v0.1.0`
