# HERISK 保护规划知识库 · 后端

知识库的本地 Python 后端，配套前端页面 `knowledge.html` 与主站"规划反馈响应"页签使用。

## 组成

- `heritage-knowledge/` — 知识库核心：
  - `kg.py` — KnowledgeBase：文档管理、中英检索、规划证据包（planning_bundle）
  - `llm.py` — DeepSeek 生成（策略草案、关系抽取），未配置密钥时仅返回能力状态
  - `cli.py` — 构建工具（`python cli.py build`）
  - `ontology.json` — 领域本体（五类危害、干预措施等）
  - `scripts/ tests/ reports/` — 构建脚本、测试与审计报告
- `knowledge_api.py` — HTTP 接口：`/api/knowledge/status | search | documents | plan | document | generate`

## 本地运行

1. **数据与 PDF 不进 git**（体积与版权考虑，已在 `.gitignore` 排除）：
   请在开发机保留 `heritage-knowledge/data/`（含 `knowledge.sqlite` 索引）与 `heritage-knowledge/reference/`（PDF 原文），
   或在本目录运行 `python cli.py build` 重新构建。
2. **配置 DeepSeek（可选）**：复制 `.env.example` 为 `.env` 并填写密钥；检索功能不需要密钥。
3. **挂载接口**：在 `server.py` 中 `from knowledge_api import handle as handle_knowledge`，
   对 `/api/knowledge/*` 的请求转发给 `handle_knowledge`，启动后即可使用。

## 在线说明

GitHub Pages 为纯静态托管，不运行 Python。线上 `knowledge.html` 与主站规划页签会如实显示
"知识服务未接入"，完整检索、文献与 AI 生成需在本地启动后端。
