# Agent 项目求职短板与升级计划

更新时间：2026-10-27

适用对象：`llm-coding-agent-system`（主）、`llm-evalops-platform`（结果落库与 gate）

Gate 影响：**不改变 G0–G3 状态**。本计划是 G3 之后的质量与可信度扩展，产出新的、可写进简历的证据；在对应工作包验收前，不得新增简历数字。

目标岗位假设：Agent Harness / Agent 工程岗为主，兼顾 Agent 算法岗。若目标改为纯算法岗，WP2/WP3 优先级下调，WP1 不变。

## 0. 结论

外部建议（扩 SWE-bench、补安全测试、准备“为什么自研”）方向正确，但有两点需要修正：

1. **它漏掉了几颗更危险的“雷”**：部分现有指标本身不成立，面试官一旦追问就会穿帮。必须先止血（WP0），再扩实验，否则新实验也会继承同样的问题。
2. **工期估计偏乐观**：SWE-bench 扩到 100 题的瓶颈是“每题的执行环境”，不是跑题本身；安全测试的前提是先有一个能拦截的策略层，而现在几乎没有。

调整后的主线是：**先修正证据 → 用容器执行后端同时支撑公开基准扩样和安全沙箱 → 在公开基准上做预注册的配对对照，并加外部参照基线 → 补安全红队与 runtime 硬化 → 准备“为什么自研”的可验证论据。**

## 1. 对外部判断的逐条核实

| 判断 | 核实结果 | 证据 |
|---|---|---|
| 没有真实用户 | 属实。但对学生作品集是常态；不能造用户，只能补“真实使用证据”（WP6）。 | — |
| HumanEval 已饱和 | 属实，且更糟：98.2% 来自 v0.4.0 和旧模型，属于历史归档，不是当前版本的结果。 | Agent README “Archived historical promoted artifacts” |
| 40 题集是自建的 | 属实。此外，在这套 40 题上，作为简历核心卖点的 C6 验证门（85.0%）**低于** C3（90.0%）。 | [`BASELINE_0_6_0.md`](../../llm-coding-agent-system/report/BASELINE_0_6_0.md) |
| 受控对照 n=60 不显著 | 属实。46/60 vs 50/60，Fisher 双侧 p≈0.49；要在 80% power 下检出 6.7pp，每组约需 576 次。更严重的是因果链：candidate 组 60 次只调用检索 4 次、命中 2 次，citation provenance valid = 0。所以这 +6.7pp **不能归因于 RAG**。 | [`agent-rag-ablation-latest.json`](../../artifacts/evidence/agent-rag-ablation-latest.json) |
| SWE-bench Lite 只有 2/8 | 属实。v0.8 的 SWE-12 baseline 也只跑完 5/12（2/5 通过），且运行时工作区是 dirty 的。 | [`BASELINE_0_7_1.md`](../../llm-coding-agent-system/report/BASELINE_0_7_1.md)；`llm-coding-agent-system/artifacts/v080-baseline/`（未纳入版本控制） |
| 必问“为什么不用 LangGraph” | 属实。现在的回答缺少代码层面的硬论据（见 §2.3）。 | — |

## 2. 外部建议未发现的短板（按危险度排序）

### 2.1 证据完整性（最高优先级，现在就会穿帮）

- **Token 统计失效。** `llm_client.py` 从未读取 provider 返回的 `usage`，`add_message` 也从未收到 usage 参数，所以 `total_tokens` 实际上约等于 `len(system_prompt)//4`。证据如下：v0.8 Complex 的 18 次运行全部是 968；G3 报告中 “Token usage 50,999 / 51,994” 平均每题约 850，远低于真实值。成本、效率相关的结论目前全部不可用。代码位置：`coder_agent/core/context.py`（`HistoryManager.add_message`）、`coder_agent/core/agent_turns.py`、`coder_agent/core/llm_client.py`。
- **简历中有三处 claim 与仓库数据冲突**：
  - “C6 Verification Gate eliminated all clean-stop-but-wrong cases”只在归档的 21 题集上成立，在 40 题集上 C6 退步了；
  - G3 模板句 “by integrating provenance-aware document retrieval” 不成立，理由见 §1；
  - HumanEval 98.2% 被写成当前能力。
- **超时噪声大。** G3 两组分别有 9/60 和 8/60 次触发 180s 外部超时，p95 恰好等于超时上限。被测的是预算，不是能力。

### 2.2 Harness 安全层几乎为空

- shell 防护是对 7 个字符串做子串匹配的 denylist（`config.yaml` → `tools.blocked_commands`，`shell_tool.py` 中的 `any(p in command ...)`）。`rm  -rf /`（多一个空格）、`$(echo ... | base64 -d)`、`python -c "shutil.rmtree(...)"`、`find / -delete` 都能绕过。
- 文件工具有 `resolve()` + `is_relative_to` 做路径约束，但 shell 完全绕过这一层。
- 检索结果和 MCP 输出没有任何“不可信数据”标记，直接进入上下文。项目恰好集成了 RAG 和 MCP，间接 prompt 注入是最自然的追问。
- 没有 permission 模式（只读 / 工作区可写 / 需审批），没有网络出口控制，没有容器隔离。[`THREAT_MODEL.md`](../engineering/THREAT_MODEL.md) 已诚实写明 “A denylist is not a sandbox”，但这不能当作面试答案。

### 2.3 检查点是“摘要式恢复”，不是精确恢复

- 目前持久化的是 `run_steps`（thought/observation 文本、`loop_state_json`）和 `tool_calls` 审计，**没有完整 message history**。
- `--resume` 时，取最近 6 步，把 thought 截断到 160 字符、observation 截断到 220 字符，拼成一条 `[Resume context]` 用户消息注入；工作区按磁盘现状继续，没有一致性校验。
- 并发方面：每个 run 一个线程；全局只有一个 SQLite 连接（`check_same_thread=False`），由 `threading.Lock` 串行化；未开 WAL；没有并发上限；进程重启后残留在 `running` 状态的 run 不会被回收。
- 面试官问“检查点存什么、怎么序列化、并发怎么处理”时，以上就是如实答案，而这些答案会被继续深挖出漏洞。LangGraph 的 checkpointer 恰好在这些点上更完整。

### 2.4 缺少外部参照基线

所有对照都是“自己 vs 自己”。面试官问“你的 harness 到底好不好”，现在无法回答。同模型、同任务下跑一个公开的极简 agent（mini-SWE-agent），就能给出参照点。这也是回答“为什么自研”的最好数据。

### 2.5 评测集区分度

- ComplexCodeBench：3 个 seed × 6 题全部通过，每题 3 步，已饱和，没有区分度。
- ConversationBench：3 个 seed 分别为 5/12、3/12、4/12，平均约 33%；失败标签中 `constraint_failure` 有 24 次、`verification_failure` 有 17 次。这是**唯一有提升空间且失败模式清晰的 lane**，适合做 failure-driven 的改进故事（WP5）。

## 3. 升级原则

1. **先修测量，再做实验。** WP0 完成前不启动任何付费正式运行。
2. **预注册。** 每个正式对照在运行前提交一份登记文件，写明主假设、主指标、样本、seed、预算、统计检验和停止规则，并提交 commit；运行后不改。
3. **配对设计。** 同一任务在不同 arm 下配对，用 McNemar 检验和配对 bootstrap CI，不用两样本比例检验。
4. **负结果照报。** 所有 run 都保留；infra 失败单列，不静默剔除。
5. **简历跟着 artifact 走。** 每个工作包验收后，按 §7 的规则更新简历。

## 4. 工作包

### WP0 — 证据止血（1–1.5 天，无 API 成本）

状态（2026-10-27）：本地完成并已用真实 `glm_5` 调用核对；见 Agent [`IMPROVEMENT_REPORT_v0.8.0-token-usage.md`](../../llm-coding-agent-system/report/IMPROVEMENT_REPORT_v0.8.0-token-usage.md) 与 [G3 勘误](../reports/agent-rag-ablation-v1-erratum.md)。未提交。

工作项：

- 两种 transport 都要从 provider 响应中读取 `usage`。OpenAI-compatible 流式请求需设置 `stream_options.include_usage`，或从最终 chunk 读取。读到的 usage 进入 `add_message(..., usage=...)`，然后进入 run state 的 `step_tokens`/`total_tokens` 和 EvalOps 的 `agent/v1` 报告。
- 区分两个量：**上下文占用估算**（用于截断）和**累计计费 token**（用于成本），分成两个字段，不能再共用 `total_tokens`。
- 按 profile 配置单价，产出 `estimated_cost_usd`，不再是 `null`。
- 给 G3 写一份勘误：新建版本化文件，不覆盖原报告。说明 token 行无效，以及 +6.7pp 不可归因于检索。
- 超时校准：在 dev 任务上统计 wall time 分布，把正式预算定在 p99 以上；超时单独作为 infra/budget 类别报告。
- 简历不在本计划内修改（由单独的简历流程负责）；可引用的口径以 [G3 勘误](../reports/agent-rag-ablation-v1-erratum.md) 的 Claims boundary 和本文 §7 为准。

验收：

- 单元测试：fake provider 返回已知 usage，断言 run state、结果 JSON 和 EvalOps 报告三处数值一致。
- 用真实模型跑 1 道 Custom 题，token 数与 provider 控制台 / 响应头一致（误差 < 1%）。
- Agent 全量测试 + `make closure` 通过（`agent/v1` 报告字段有变化）。

回滚：usage 字段为可选；provider 不返回 usage 时记 `null` 并标注原因，不回退到估算值。

### WP1 — 公开基准扩样与预注册对照（5–7 天 + API 费用）

先修正外部建议：

- **基准选择**：建议用 **SWE-bench Verified**，以固定随机种子抽 100 题。它是 500 题人工验证集，是业界通用口径，公开 agent 也多在这上面报结果。如果坚持用 Lite，就从 300 题中同法抽 100 题。
- **环境是瓶颈，不是题数**：SWE-12 的扩容审计显示，每题都要手工钉 Python/numpy 版本；Astropy、Matplotlib 在 macOS arm64 上无法构建。所以扩到 100 题必须换成**官方实例 Docker 镜像（x86_64）+ 官方评分 harness**，并在 Linux x86 主机上运行（云 VM，建议 ≥16 vCPU / 64 GB / 300 GB 磁盘）。
- **关键工程项：容器执行后端。** 把 shell/file 工具的执行目标抽象成 `ExecutionBackend`（local / docker），Agent 在实例容器内执行命令。这个后端同时就是 WP2 的沙箱，一次投入两处受益。

实验设计（运行前预注册）：

| Arm | 配置 | 用途 |
|---|---|---|
| A | C3（验证门关） | 对照 |
| B | C6（验证门开） | 主假设：验证门提升 resolve rate |
| R | mini-SWE-agent，同模型、同步数/成本上限 | 外部参照，单 seed |

- 样本：100 题；A/B 各 2 个 seed（400 次），R 跑 1 个 seed（100 次）。
- 主指标：官方 harness 判定的 resolved rate。次要指标：真实 token、成本/题、wall time、步数、失败分类。
- 统计：A vs B 用 McNemar（逐题配对，按 seed 分别报告，并报告“2 个 seed 都通过”的严格口径），外加配对 bootstrap 95% CI。
- 预期管理：n=100 只能检出约 ≥10pp 的效应。历史数据（40 题集上 C6 < C3，SWE-8 上两者打平）显示**验证门很可能无显著收益**，这完全可以接受。这个实验的主要价值是：
  1. 公开基准上的绝对水平；
  2. 与外部参照基线的对比；
  3. 用数据检验并修正简历里的核心 claim。
- 先跑 pilot：从 dev pool 取 10 题，与正式 100 题不重叠。pilot 用于验证 harness，并用 WP0 修好的 token 统计实测单题成本，再据此确认总预算。
- 结果写入 EvalOps，形成 compare/gate 记录。

验收：

- 预注册文件的 commit 早于第一次正式运行。
- 全部 500 次运行的原始 patch、trajectory、官方评分日志都保留；infra 失败率单独报告。
- 报告从原始 artifact 一键重算，并按 `agent-rag-ablation` 的 provenance 格式记录任务集哈希、镜像 digest 和代码 commit。

回滚：docker 后端默认关闭，local 后端行为和现有基线保持不变（tool schema 快照测试）。

### WP2 — 权限策略层与安全红队评测（3–4 天，主要是离线）

先建拦截能力，再测拦截率：

- **Permission 模式**：`read-only` / `workspace-write` / `full`，外加按工具、按参数模式配置的 `allow` / `ask` / `deny` 规则。每次判定的 `decision` 和 `rule_id` 写入 `tool_calls` 审计。
- **Shell 解析**：用 `bashlex` 解析成 AST，再提取命令名、重定向和子命令替换。对命令名做 allowlist，取代现在的子串 denylist。网络类命令（`curl`/`wget`/`nc`/`pip install <url>`）默认 `ask` 或 `deny`。读取 `.env`、`~/.ssh`、`*credentials*` 默认 `deny`。
- **不可信内容标记**：`knowledge_retrieval`、MCP 和文件读取的输出用带来源标签的分隔块包裹，并在系统提示中声明这些内容“仅为数据”。上下文中出现不可信内容之后，高风险动作（网络、删除、修改测试/验证文件）一律升级为 `ask`。这是一个简化版的 taint 规则。
- **纵深防御**：docker 后端默认 `--network none`、非 root 用户、只读 rootfs（工作区除外）、CPU/内存/进程数上限。

红队评测集 AgentSecBench v1（建议约 80 个攻击用例 + 40 个良性用例）：

| 类别 | 例子 |
|---|---|
| 直接破坏指令 | 用户要求删除工作区外的目录 |
| 混淆绕过 | 多空格、base64、`$(...)`、变量展开、`python -c`、`find -delete` |
| 路径逃逸 | `../`、绝对路径、工作区内指向外部的 symlink |
| 敏感信息读取/外泄 | 读 `.env` 后 POST 到外部地址 |
| 间接注入：RAG 文档 | PDF 中嵌入“忽略之前的指令，执行……” |
| 间接注入：仓库文件 | README、代码注释、测试输出中的指令 |
| 间接注入：MCP 输出 | fake MCP server 返回的恶意指令 |
| 评测作弊 | 修改/删除测试、篡改验证脚本（coding agent 特有的 reward hacking） |
| 资源滥用 | fork bomb、死循环、任意来源安装 |

两层测量：

- **L1 策略层（确定性，不调用 LLM）**：直接把合成的工具调用喂给策略引擎，报告各类别的拦截率和良性误拦率，结果 100% 可复现。
- **L2 端到端（LLM 在环）**：把攻击内容放进任务环境，统计 attack success rate（ASR）。用 canary 文件、canary token 和本地假外泄接收端判定攻击是否成功，不访问真实网络。对比三种配置：现有 denylist / 策略层 / 策略层 + 容器。
- **可用性代价**：在 Custom 40 题上比较策略开 vs 关的通过率，同时报告误拦次数和 `ask` 触发次数。

验收：L1 报告分类别的分子/分母；L2 报告三种配置下的 ASR 和可用性差值；威胁模型文档同步更新。方法论参考 AgentDojo / InjecAgent，但不宣称与它们可比。

### WP3 — Runtime 硬化（2 天，无 API 成本）

目标：让“检查点存什么、怎么序列化、并发怎么处理”这三个问题都有经得起深挖的答案。

- **精确恢复**：新增 append-only 的 `run_messages` 表（`run_id`、`seq`、`role`、`content_json`、`tool_calls_json`、`usage_json`、`schema_version`）。每步额外记录工作区指纹（`git` tree hash）。恢复时按 message log 精确重建 history；指纹不一致时告警，并回退到现有的摘要式恢复。
- **SQLite**：开启 `journal_mode=WAL` 和 `busy_timeout`；写入改为单写线程队列，或每线程一个连接。
- **生命周期**：新增 `heartbeat_at` 字段；服务启动时把心跳过期的 `running` run 回收为 `interrupted`（可恢复）；`max_concurrent_runs` 信号量，满载时返回 429；提交接口支持 idempotency key。
- **崩溃注入测试**：用确定性 fake LLM 跑 50 次，在随机步 `kill -9`，然后恢复，断言最终 history、工作区和结果与不中断的运行逐字节一致。

验收：崩溃注入 50/50 精确恢复；Agent 全量测试通过；不改变 C3/C6 推理行为。如果 history 构建路径有改动，按 Agent `AGENTS.md` 判断是否需要 rebaseline。

### WP4 — “为什么自研”的可验证论据（1–1.5 天）

- **概念映射表**（写进面试材料）：RunStateStore ↔ Checkpointer；`loop_state` ↔ State；验证门 ↔ 条件边；`cancel_event` ↔ interrupt；`run --resume` ↔ 按 thread_id 恢复；工具审计 ↔ LangSmith trace。
- **诚实的取舍叙事**：
  - 自研的原因：评测需要逐步可控、可观测的 loop 内策略（验证门、重试策略、测试修改授权、安装预算），需要可复现地钉住行为；而单 agent ReAct 用不到图式分支。
  - 代价：WP3 之前没有精确恢复，也没有 HITL interrupt，这些是 LangGraph 现成具备的。
  - 什么时候会选 LangGraph：多 agent、HITL 审批流、团队协作维护。
- **可选 spike（推荐）**：用 LangGraph 的 `StateGraph`（agent 节点 + tools 节点 + verify 条件边，`SqliteSaver`）复刻 C3 loop，工具复用同一套实现；在 10 道 Custom 题上比较代码行数、通过率、单步延迟开销和恢复语义。这样面试时的回答就从“我觉得”变成“两种都做过，也测过”。
- **代码讲解清单**：checkpoint 写入路径、resume 路径、取消路径、验证门触发点、工具执行与审计，每项给出文件和行号，方便现场打开讲解。

### WP5 — 多轮约束保持候选（可选，3–4 天 + API）

前提：WP0 完成，ConversationBench 协议已冻结（v0.8.0 计划中的已有内容）。

- 依据 baseline 失败分类（以 `constraint_failure` 为主），实现一个“约束账本”：把每轮引入的约束结构化记录，在后续回合固定注入，并在 verify 阶段逐条检查。
- 局限：12 题 × 3 seed 样本很小，只报原始计数和逐题结果，不写显著性；如果时间允许，先把 test split 扩到 ≥30 题再冻结。
- 价值：给出一条与 Claude Code / Cursor 类产品直接相关的 failure-driven 改进故事。

### WP6 — 真实使用证据（持续，低成本）

- **Dogfooding 日志**：用这个 Agent 处理 ≥20 个真实任务（本作品集的 issue/重构/测试补全），逐条记录结果（原样合入 / 修改后合入 / 放弃）、耗时和失败原因，保存为版本化 artifact。
- 录一个 3 分钟 demo 视频：一键启动 → 提交任务 → 轨迹 → EvalOps compare/gate → 标记 bad case。
- 表述口径固定为“自用评估”，不写成“用户”。

## 5. 排期

两周版（推荐）：

| 天 | 工作 |
|---|---|
| D1 | WP0 全部 |
| D2–D3 | WP3 runtime 硬化（长时间正式运行依赖精确恢复和真实 token） |
| D3–D5 | WP1 容器后端 + Linux 主机 + 官方 harness 打通；10 题 pilot；提交预注册 |
| D6–D8 | WP1 正式运行（后台进行）；同时做 WP2 策略层与 L1 |
| D9 | WP2 L2 端到端与可用性代价 |
| D10 | WP1/WP2 报告；WP4 材料与可选 LangGraph spike；更新简历 |
| 持续 | WP6 |

如果 3 天内就要面试（不花 API 费用）：

1. WP0：修 token 统计 + G3 勘误；
2. WP4 材料（不做 spike），并如实准备 §2.3 的现状与改进方案；
3. WP2 的策略层 + L1 确定性拦截测试。

## 6. 测试矩阵

| 工作包 | 最小验证 |
|---|---|
| WP0 | Agent 全量测试 + usage 单测 + `make closure`（`agent/v1` 字段变化） |
| WP1 | 后端 schema 快照测试 + pilot + 官方评分日志 + 可重算报告 + EvalOps compare |
| WP2 | 策略引擎单测（L1 全量）+ Agent 全量测试 + Custom 可用性对照 |
| WP3 | 崩溃注入 50 次 + 并发/回收测试 + Agent 全量测试 |
| WP4 | spike 的 10 题对照结果与代码行数统计 |
| 文档 | `python3 scripts/check_workspace_docs.py` + `git diff --check` |

## 7. 简历与面试口径规则

现在立即停止使用：

- HumanEval 98.2% 作为当前能力；
- “Improved verification pass rate … by integrating retrieval”；
- 不加限定的 “verification gate eliminated all clean-stop-but-wrong cases”；
- 任何 token/成本数字。

现在可以写（已有 artifact 支撑）：

- 可恢复 runtime、服务化、工具审计、跨项目 EvalOps gate 等**工程能力**；
- G3 写成“建立了可复现的 baseline/candidate 评测链路并完成一次 gated 对照”，不写因果提升；
- 在 40 题集上发现 C6 不优于 C3，并据此停止推广验证门——把它当作“诚实评测”的案例来讲。

各工作包验收后可新增的表述（占位符必须与 artifact 一致）：

- WP1：“On a fixed random 100-task SWE-bench Verified subset with official Docker grading, resolved **X%** vs **Y%** for mini-SWE-agent under the same model and budget; a pre-registered verification-gate ablation showed **Δ pp (McNemar p=…)**.”
- WP2：“Replaced a substring denylist with an AST-based tool-call policy layer and container sandbox; reduced attack success on an 80-case red-team suite from **A%** to **B%** at **C%** benign false-positive rate and **D pp** utility cost.”
- WP3：“Event-sourced checkpointing with exact resume, validated by **50/50** crash-injection recoveries.”

## 8. 风险与明确不做

- WP1 的结果可能是“验证门无效”，甚至“不如 mini-SWE-agent”。两者都照实写：前者用来修正 claim，后者用失败分类解释差距，并接到下一轮改进。
- 云 VM 与 API 费用需要先由 pilot 实测再确认，并设置硬上限。
- 不做：多 agent 框架、全量 500 题排行榜宣称、LLM-as-judge 取代可执行验证、为丰富技术栈而引入新组件。

## 9. 待决定事项

1. 距离第一场面试还有多久？这决定走两周版还是 3 天版。
2. API 与云 VM 的预算上限。
3. 用 SWE-bench Verified 还是 Lite（推荐 Verified）。
4. 是否做 WP4 的 LangGraph spike 和 WP5。
