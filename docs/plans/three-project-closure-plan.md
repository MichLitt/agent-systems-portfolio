# 三项目闭环落实计划

更新时间：2026-08-06

## 0. 执行状态

状态：**已完成并验证**

- [x] RAG Phase 3 / Phase 5 分支合并；当前分支不再落后 `origin/main`。
- [x] RAG 离线 tokenizer fallback、统一 `--data-dir`、安全 `index_id` 已实现。
- [x] Agent `knowledge_retrieval` 已完成、默认关闭、配置后自动注册。
- [x] EvalOps 对 `agent/v1`、`rag/v1` 执行真实 Pydantic 契约校验。
- [x] 两类 run 均可 normalize、query、compare、gate，release decision 已持久化。
- [x] 三项目本地测试：Agent 275 passed；EvalOps 45 passed；RAG 415 passed、1 optional skip。
- [x] `./scripts/run_three_project_closure.sh` 真实 HTTP 闭环通过。
- [x] 机器可读证据：`artifacts/closure/three-project-closure-latest.json`。

未纳入本轮完成定义的事项仍为：外部模型/大索引压测、GitHub push/PR、线上部署和 Finetune producer。

## 1. 目标与范围

本计划只覆盖以下三个项目：

1. `rag-benchmark-system`：提供 PDF/OCR ingestion、可查询索引和带来源页码的 retrieval API。
2. `llm-coding-agent-system`：把 RAG retrieval API 暴露为 Agent 工具，并在 run 结束后上报 Agent summary。
3. `llm-evalops-platform`：接收 RAG/Agent 报告，标准化、查询、compare，并通过 release gate 形成发布决策。

最终闭环：

```text
PDF -> RAG ingest/index -> Agent knowledge_retrieval -> Agent/RAG reports
    -> EvalOps ingest/normalize -> compare -> release gate
```

本轮不包含模型训练、Finetune producer、线上部署和远端仓库发布。

## 2. 完成定义

只有以下证据全部成立，三项目闭环才算完成：

- RAG 本地 Phase 3 与远端 Phase 5 能力已合并，工作树不存在未解决分叉。
- RAG ingestion/retrieval 在首次运行无网络时也可工作，测试不因 tokenizer import-time 下载失败。
- Agent 的 `knowledge_retrieval` 工具有参数校验、超时、HTTP/JSON 错误处理、来源和页码输出。
- RAG API 未配置时不会向 Agent 暴露不可用工具；配置后工具自动注册。
- Agent 与 RAG 的真实上报 payload 均能被 EvalOps schema/adapter 接收并标准化。
- 同一 task set 的 baseline/candidate 可 compare，并能生成持久化 release decision。
- 存在一个可重复执行的本地 E2E 脚本，不需要外部 LLM、向量模型、API Key 或云服务。
- 三个项目的完整本地测试通过；外部模型/大数据测试如未执行，必须单独列出，不能混作通过。
- 三个 README 的运行说明、当前状态与真实代码一致。

## 3. 工作分解

### M1：仓库与可复现性收敛

#### RAG

- 合并 `main` 的 OCR/async ingest 提交与 `origin/main` 的 Phase 5 citation/NLI 提交。
- 将 tiktoken 初始化从 import-time/强联网依赖改为可离线工作的实现。
- 保持原有 token-aware 行为；fallback 必须显式记录 warning，且只在编码资源不可用时启用。
- 运行 RAG 全测试，区分代码失败与可选外部模型测试。

验收：

```bash
cd rag-benchmark-system
uv run pytest -q
```

### M2：Agent Knowledge Tool 产品化

- 完成 `coder_agent/tools/knowledge_retrieval.py`。
- 仅当 `RAG_API_URL` 已配置时注册工具，避免改变未启用用户的默认工具集合。
- 覆盖以下路径：成功、空结果、未配置、超时、非 2xx、坏 JSON、字段缺失、`top_k` 边界。
- README 增加 RAG 接入配置和端到端启动顺序。
- 按 `AGENTS.md` 写 improvement report；评估是否触发 rebaseline。

验收：

```bash
cd llm-coding-agent-system
uv run pytest -q
```

### M3：EvalOps 契约闭合

- 使用两个 producer 的真实 dataclass payload 建立契约测试，而不是手写近似 JSON。
- 验证 ingest 幂等、worker normalize、run query、compare、gate 和 decision persistence。
- 明确 service run 无 task set、不能 compare；eval run task set hash 稳定。
- 更新过期的 `PROJECT_PLAN.md` 勾选状态，并保留 Phase 5 未完成项。

验收：

```bash
cd llm-evalops-platform
uv run pytest -q
```

### M4：三项目 E2E

新增根目录脚本，完成以下本地流程：

1. 使用临时 SQLite 启动 EvalOps API 和 normalizer。
2. 使用临时目录启动 RAG API。
3. 上传一个本地生成的两页 PDF，等待异步 ingestion 完成。
4. 通过 Agent `KnowledgeRetrievalTool` 查询 PDF，断言返回来源和页码。
5. 上报两个 RAG eval run，normalizer 后进行 compare/gate。
6. 上报两个 Agent eval run，normalizer 后进行 compare/gate。
7. 查询 release decisions，输出机器可读 closure summary。
8. 所有服务和临时文件在成功或失败后都被安全清理。

验收：

```bash
./scripts/run_three_project_closure.sh
```

脚本成功退出时必须打印：

```text
RAG_INGEST=passed
AGENT_RETRIEVAL=passed
RAG_EVALOPS_GATE=promoted
AGENT_EVALOPS_GATE=promoted
THREE_PROJECT_CLOSURE=passed
```

## 4. 发布门槛

### 必须完成

- 三项目单元/集成测试全绿。
- 根目录 E2E 全绿。
- 无未解决 merge conflict。
- 所有新增代码都有对应测试。
- README 命令可直接复制运行。
- Agent 行为变更有报告，并明确 rebaseline 结论。

### 本轮不阻塞但需记录

- 真实 21M Wikipedia 索引压测。
- 真实 OCR 二进制兼容性矩阵。
- HHEM 模型在线下载与 GPU 性能。
- 正式 SWE promoted C3/C6 付费模型复跑。
- GitHub push、PR 和线上部署。

## 5. 实施顺序

1. 先合并和修复 RAG，确保下游依赖的 API 稳定。
2. 再完成 Agent 工具与测试。
3. 再补 EvalOps producer 契约测试。
4. 最后实现根目录 E2E、更新文档并执行完成审计。

任何阶段发现 API/schema 不一致时，以真实 producer dataclass 和已测试的 HTTP response model 为共同契约，三边同步修改，不通过兼容 shim 掩盖不一致。
