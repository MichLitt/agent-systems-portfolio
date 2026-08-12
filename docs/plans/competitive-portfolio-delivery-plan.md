# Agent Systems Portfolio 阶段性交付计划

更新时间：2026-08-12

当前阶段：**G1 Release Baseline 已完成（v0.1.0）；G2 Demo-Ready Product 进行中**

竞争力门槛：**G2 Demo-Ready Product**

强简历门槛：**G3 Evidence-Backed Flagship**

## 1. 交付目标

本计划把四个仓库收敛为一个可以公开克隆、稳定运行、现场演示并用量化证据说明价值的 Agent 工程项目。最终叙事不是“四个 Python 项目”，而是：

> A production-style coding-agent platform with resumable execution, document intelligence, versioned evaluation, release gates, and evidence-backed system improvements.

交付必须同时满足四类要求：

1. **工程可信**：版本、CI、Submodule、契约、迁移和测试可复现。
2. **产品可见**：一条命令启动，存在清晰的用户流程和 review 页面。
3. **指标可证**：baseline/candidate 使用相同任务集，结果进入 EvalOps 并通过 gate。
4. **表达可审计**：每条简历数字都能回溯到版本化 artifact、配置和 commit。

Finetune 是可选研究扩展，不阻塞核心 Agent 平台达到 G2/G3。

## 2. 当前基线

截至 2026-08-12，本地 `make check` 已验证：

- Agent：275 tests passed。
- EvalOps：45 tests passed。
- RAG：415 tests passed，1 optional-model skip。
- Finetune：5 个核心 CLI smoke passed，真实训练尚未执行。
- PDF → RAG ingest → Agent retrieval → Agent/RAG reports → EvalOps compare/gate 闭环通过。
- Agent 与 RAG release gate 均为 `promoted`。

已完成：四个子项目 PR 合并、五仓 CI、顶层 Submodule 收敛和 `v0.1.0` 发布说明。
尚未完成：一键服务编排、EvalOps review loop、RAG job 持久化、RAG-enabled Agent 对照实验。

## 3. 阶段定义

| Gate | 交付定义 | 简历使用边界 | 当前状态 |
|---|---|---|---|
| G0 Engineering Closure | 三核心项目测试和真实 HTTP 闭环通过 | 可描述“built/integrated”，不可称 production-ready | **Ready** |
| G1 Release Baseline | 改动进入各自 `main`；全仓 CI；Submodule 固定 main；release tag/notes | 可作为公开工程项目列出 | **Ready** |
| G2 Demo-Ready Product | 一键启动；seeded demo；EvalOps review loop；RAG job 可恢复；基础安全与运行手册 | **达到有竞争力项目的最低门槛** | **In progress** |
| G3 Evidence-Backed Flagship | 固定任务集上完成 Agent baseline vs RAG candidate；质量/成本/延迟可比较；gate 和报告可复现 | 可写量化提升、作为旗舰项目展开 | **Planned** |
| G4 Post-Training Extension | 数据、污染报告、baseline、SFT/DPO 和 `finetune/v1` 全部有 artifact | 可增加模型训练亮点，不阻塞主线 | Optional |

阶段必须顺序晋级。未满足前置 Gate 时，不得仅凭局部功能宣称更高阶段完成。

## 4. G1 — Release Baseline

目标工期：2–3 个工作日。

### 工作包

#### G1.1 合并与版本收敛

- 将 Agent #12、EvalOps #1、RAG #4、Finetune #1 从 Draft 转为 Ready。
- 确认每个 PR 的 required checks 通过后合并。
- 四个子仓库本地切回 `main` 并 fast-forward。
- 更新顶层 Submodule 指针，使每个指针等于对应 `origin/main`。
- 删除不再需要的远程功能分支。

#### G1.2 CI 与发布治理

- EvalOps、RAG、Finetune 增加项目级 GitHub Actions。
- 顶层仓库增加 recursive-submodule CI，执行 docs、核心 tests、Finetune smoke 和 closure。
- main 开启 required checks；禁止未通过 CI 的直接合并。
- 创建 `docs/releases/v0.1.0.md`，记录范围、已知限制和验证命令。
- 顶层仓库打 `v0.1.0` tag。

### 验收证据

- 五个仓库 main CI 绿色。
- `git submodule status` 中四个 SHA 均等于各自 `origin/main`。
- `make check` 通过。
- `v0.1.0` tag 和 release notes 存在。
- `python3 scripts/check_delivery_readiness.py --require release` 通过。

## 5. G2 — Demo-Ready Product

目标工期：7–10 个工作日。完成后可以把项目作为有竞争力的 Agent 工程项目写入简历。

### 用户演示路径

```text
docker compose up
  -> 上传 PDF
  -> RAG job 可查询且服务重启后仍存在
  -> 提交 Agent repository task
  -> 查看 steps / tool calls / retrieved citations
  -> 查看 EvalOps baseline/candidate compare
  -> 标记 bad case
  -> 查看 promoted/rejected release decision
```

### 工作包

#### G2.1 一键环境与可观测性

- 已实现（待 Docker runtime 验收）：顶层 Compose、Agent/RAG/EvalOps API 与 worker 服务、持久化 volumes、healthcheck、无外部模型的 demo seed，以及 operations runbook。
- 为 Agent、RAG、EvalOps API、EvalOps Worker 提供容器配置。
- 顶层 `compose.yaml` 包含 healthcheck、持久化 volume 和确定性 demo seed。
- 增加 request/run correlation ID、结构化日志和启动失败诊断。
- 编写 `docs/engineering/OPERATIONS_RUNBOOK.md`：启动、停止、备份、恢复、常见故障。

#### G2.2 EvalOps Review Loop

- 已完成：bad-case 写入/查询、compare session 详情与列表 API，以及最小 Web UI（run list/detail、compare/gate 证据、bad-case tagging）。UI 只消费 `/v1` 公开 API。

#### G2.3 RAG Ingestion Reliability

- 已完成：SQLite job 表、独立 worker、claim/lease/retry/reclaim、上传与参数校验、文件 hash 幂等，以及相应 API 重启/worker crash/重复提交/失败重试测试。

#### G2.4 基础安全与演示证据

- 已完成：Agent、RAG 与 EvalOps 的业务 API 支持环境变量 token；health endpoint 保持给编排探针使用；跨项目闭环验证未携带 token 会被拒绝、携带 token 才能完成业务路径。
- 已完成：Agent shell/workspace、RAG ingestion、EvalOps evidence 的边界、已有缓解措施与残余风险已记录在 threat model。
- 生成 `artifacts/delivery/demo-readiness.json`，至少包含：

```json
{
  "schema_version": "demo-readiness/v1",
  "one_command_start": true,
  "seeded_workflow": true,
  "restart_recovery": true,
  "review_loop": true,
  "security_smoke": true,
  "passed": true
}
```

### G2 验收标准

- 新机器按 README 在 15 分钟内完成启动。
- 无外部付费 API 也能完成 seeded demo。
- RAG ingestion 在 worker/API 重启后可恢复。
- EvalOps 页面能追踪一次 run、一次 compare、一次 gate 和一个 bad case。
- 日志中无 token、完整 prompt secret 或本机绝对路径泄露。
- `python3 scripts/check_delivery_readiness.py --require demo` 通过。

### G2 简历表达模板

完成 G2 后，可以使用不带质量提升数字的工程型 bullet：

> Built a production-style coding-agent platform spanning resumable task execution, persistent document ingestion, retrieval with page-level provenance, and versioned EvalOps release gates; packaged four services into a reproducible one-command demo with automated end-to-end validation.

## 6. G3 — Evidence-Backed Flagship

目标工期：5–8 个工作日。

### 实验设计

- 冻结一个公开、可重放的 repository-task 子集，建议 20–30 个任务。
- Baseline：Agent 不注册 `knowledge_retrieval`。
- Candidate：Agent 注册 RAG，并使用固定文档索引。
- 固定模型、temperature、预算、任务、代码 commit 和 verification commands。
- 至少运行 3 个 seeds；失败重试不得只选择性保留成功结果。

### 必须报告的指标

- task success / verification pass rate
- tool success rate / retry rate
- retrieval hit and citation correctness
- wall latency / p50 / p95
- token usage and estimated cost
- failure taxonomy distribution

### 交付物

- EvalOps 中持久化 baseline/candidate runs、compare session 和 gate decision。
- `artifacts/evidence/agent-rag-ablation-latest.json`，至少包含：

```json
{
  "schema_version": "agent-rag-ablation/v1",
  "task_count": 20,
  "seed_count": 3,
  "baseline_run_ids": [],
  "candidate_run_ids": [],
  "metrics": {},
  "gate_decision": "promoted",
  "passed": true
}
```

- `docs/reports/agent-rag-ablation-v1.md`，说明假设、实验设计、结果、限制和失败案例。
- 固定配置、task manifest、commit SHA 和原始机器可读结果。

### G3 验收标准

- baseline/candidate task set 完全一致。
- 指标和报告可以从原始 artifact 重新计算。
- required gate 为 `promoted`；否则诚实记录 rejected，不写提升 claim。
- 至少包含一个负面或无提升结果，说明不是 cherry-pick 展示。
- `python3 scripts/check_delivery_readiness.py --require evidence` 通过。

### G3 简历表达模板

只有数值与 artifact 一致时，才能替换占位符：

> Improved repository-task verification pass rate from **X% to Y%** across **N tasks / S seeds** by integrating provenance-aware document retrieval into a resumable coding-agent runtime, while holding model and execution budgets constant; automated comparison and promotion through versioned EvalOps release gates.

## 7. G4 — Finetune Extension（非阻塞）

执行顺序必须为：

1. 生成训练数据和数据统计。
2. 运行 contamination gate 并保存报告。
3. 跑同一 Qwen3.5-4B-Instruct zero-shot baseline。
4. 跑 `sft_generic` 和 `sft_targeted`。
5. 只有 SFT 在 held-out 指标上稳定改善时才运行 DPO。
6. 新增真实 `finetune/v1` producer、adapter、contract tests 和 release gate。

HumanEval 始终只用于 held-out evaluation。没有 checkpoint、config、seed、硬件信息和原始结果时，不得填写 README 的 TBD。

## 8. 实施批次

| Iteration | 重点 | 完成信号 |
|---|---|---|
| I0 | PR、CI、main、Submodule、tag | G1 ready |
| I1 | Compose、health、runbook、demo seed | 四服务一键启动 |
| I2 | EvalOps review loop + RAG persistent worker | G2 ready，可写工程型简历 bullet |
| I3 | Agent/RAG controlled ablation + evidence report | G3 ready，可写量化 bullet |
| I4 | Finetune | 可选模型训练亮点 |

每个 Iteration 应拆成不超过 1–3 天的 PR；跨仓契约变更必须按 `AGENT_ENGINEERING_STANDARD.md` 同步提交 producer、consumer、tests 和 docs。

## 9. 明确不做

在 G3 前不投入：多 Agent 框架、IDE 插件、复杂权限系统、Kubernetes、多云部署、全量 SWE-bench leaderboard、无证据的 prompt 调优、仅为“技术栈丰富”新增数据库或消息队列。

优先级判断只有一个：它是否提高可复现性、演示完整性或量化证据强度。
