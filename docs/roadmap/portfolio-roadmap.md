# Agent-First AI 工程实习项目路线图

## 1. 新判断：为什么要改成 Agent-First

基于最近的岗位信号，市场更偏好的是 `Agent`，但准确地说，是更偏好下面这类能力组合：

- agent runtime
- tool use / retrieval integration
- evaluation / observability
- reliability / sandbox / release

也就是说，真正吃香的不是“我做了一个 agent demo”，而是“我能把 agent 做成一个可运行、可评测、可恢复、可上线的系统”。

这意味着之前那版 `RAG 作为旗舰` 的策略需要调整。新的更优策略是：

- 让 `llm-coding-agent-system` 成为主旗舰项目
- 让新项目 `LLM EvalOps Platform` 成为共享基础设施
- 让 `rag-benchmark-system` 转型为 agent 的文档与知识子系统
- 让 `coding-llm-finetune` 作为高质量补充项，而不是第二旗舰

最终对外叙事从：

`RAG -> Agent -> Finetune -> Platform`

改成：

`Agent Runtime -> Eval/Release Platform -> Agent Knowledge System -> Targeted Model Optimization`

这个顺序更符合截至 **2026 年 4 月 2 日** 的岗位趋势，也更适合回应“缺少大规模工程实践”的反馈。

参考信号：

- OpenAI `Software Engineer, Agent Infrastructure`
  https://openai.com/careers/software-engineer-agent-infrastructure/
- Anthropic `Model Evaluations` / careers
  https://www.anthropic.com/careers/jobs/5018714008
  https://www.anthropic.com/careers
- LangChain careers 对“生产级 agent”与平台能力的描述
  https://jobs.ashbyhq.com/langchain/8aa63e71-b431-49d7-ab4a-bf4b3630d8e6
- Agentic platform 岗位对共享运行时、评测、观测能力的强调
  https://jobs.ashbyhq.com/a-place-for-mom/7d202fc1-9a58-44ae-b119-15bf48706d62

## 2. 这版路线解决什么问题

之前的计划有 3 个主要问题：

1. 主线不够聚焦
项目很多，但没有明确告诉面试官“你最擅长的是把 agent 系统做成工程化产品”。

2. 实现点和市场热点不完全匹配
原计划里 `rag` 权重过高，`agent` 虽然有，但没有把 `runtime + eval + reliability` 做成主卖点。

3. 平台能力和业务能力没有绑定
之前提平台更多像“再开一个新项目”，现在要改成“它就是 agent 生产化的基础设施”。

新路线的目标是：

- 主项目强：有一个能压住场面的 agent 旗舰系统
- 平台味足：能体现 orchestration、tracking、gating、observability
- 业务感强：不是只做 benchmark，而是能处理真实代码仓库和真实知识上下文
- 研究补充合理：保留 finetune 的深度，但不让它抢主线

## 3. 修订后的项目优先级

最终项目排序建议：

1. `llm-coding-agent-system`
   主旗舰：`Agent Runtime and Task Execution System`

2. 新项目 `llm-evalops-platform`
   共享平台：`Agent Eval, Observability, and Release Platform`

3. `rag-benchmark-system`
   能力扩展：`Agent Knowledge and Document Intelligence System`

4. `coding-llm-finetune`
   补充亮点：`Targeted Post-Training and Inference Benchmark`

这个顺序的含义是：

- 你找的是 AI 工程师相关岗位，主叙事应该是 agent engineering
- 你需要用 platform 项目来补“大规模工程实践”
- 你需要用 RAG 子系统证明 agent 不只是会调工具，而是会处理真实知识输入
- 你需要用 finetune 项目证明你不只是应用层，还能做 failure-driven model improvement

## 4. 主旗舰：Agent Runtime and Task Execution System

项目基于：`llm-coding-agent-system`

### 4.1 新定位

不要再把它讲成“ReAct coding agent benchmark repo”。

新的定位应该是：

`面向代码仓库任务的 Agent Runtime，支持任务持久化、工具调用、验证、恢复执行、结果追踪和系统化评测。`

这才是市场上真正吃香的 agent 项目形态。

### 4.2 主亮点

这个项目要承担你的最核心简历信号：

- agent runtime design
- task orchestration
- persistent execution state
- tool safety and reliability
- verification-aware agent lifecycle
- production-style evaluation

### 4.3 必做实现点

1. 任务执行模型
- `run` / `step` / `artifact` / `tool_call` 的数据模型
- 持久化 run state
- 支持 pause / resume / retry
- 支持任务超时和取消

2. 工具调用可靠性
- tool timeout
- transient failure retry
- structured error taxonomy
- command audit trail
- sandbox boundary 明确化

3. 仓库任务闭环
- repo context loading
- file read / search / patch / test 执行
- verification gate
- result artifact 持久化

4. 服务化
- 保留 CLI
- 增加 API 服务层
- 支持异步任务提交
- 支持 run status 查询

5. 可观测性
- step latency
- tool success rate
- run success rate
- token usage
- retry count

6. 与平台集成
- 每次 run 自动上报到 `LLM EvalOps Platform`
- 保存 trajectory summary、metrics、artifacts
- 支持 benchmark replay

### 4.4 不做的内容

- 不做 IDE 插件
- 不做复杂前端 IDE
- 不做多 agent 协同框架
- 不做网页浏览自动化大而全系统
- 不做一堆花哨 prompt features

### 4.5 这个项目最后要能回答的问题

- agent 为什么需要 persistent state
- 工具调用失败时如何恢复
- verification 为什么不是末尾附加模块，而是 runtime 的一部分
- 什么指标能判断一个 agent system 是否真的可用
- 如何把 benchmark 和真实运行统一到一个 execution model

### 4.6 简历表达目标

- Built a production-style agent runtime for repository tasks with persistent run state, retryable tool execution, verification gates, and structured execution traces.
- Productized a coding agent from a benchmark prototype into an async task execution service with resumable runs, audit logging, and benchmark replay support.

## 5. 新增共享平台：Agent Eval, Observability, and Release Platform

项目基于：新增 `llm-evalops-platform`

### 5.1 新定位

这个项目不是“泛泛的 LLMOps 平台”，而是：

`专门服务 agent 与 agent-adjacent systems 的评测、观测、发布和追踪平台。`

这比通用 LLM dashboard 更有辨识度，也更贴合求职方向。

### 5.2 这个项目存在的必要性

它负责承接真正能体现“大规模工程实践”的平台层信号：

- async job orchestration
- run metadata store
- artifact tracking
- metric normalization
- compare and release gate
- bad case review

如果没有这个项目，你的其他项目很容易被看成“有功能，但不够生产化”。

### 5.3 必做实现点

1. Job orchestration
- API 提交评测任务
- queue + worker 异步执行
- job 状态机
- retry / resume

2. Metadata 模型
- app type: agent / rag / model
- dataset version
- config version
- model version
- run id / artifact path / timestamps

3. Metric registry
- agent 指标：task success、verification pass、tool failure、latency、cost
- rag 指标：answer quality、citation quality、grounding、latency、cost
- finetune 指标：benchmark score、throughput、memory、latency

4. Compare / gating
- 同任务多版本 compare
- 基于阈值的 release gate
- promoted / rejected 标记

5. Review loop
- bad case 浏览
- tagging failure mode
- 链接到 artifact 和 trajectory

### 5.4 不做的内容

- 不做复杂组织权限
- 不做企业级多租户
- 不做完整数据标注平台
- 不做全功能 MLOps 系统

### 5.5 这个项目最后要能回答的问题

- 为什么 agent 应用必须有独立 eval/observability 平台
- 不同 agent run 如何被标准化地比较
- release gate 为什么重要
- 如何从失败样本反推系统和模型改进

### 5.6 简历表达目标

- Built an evaluation and observability platform for agent systems with async job orchestration, run tracking, artifact management, metric normalization, and release gates.
- Standardized benchmarking across agent, retrieval, and post-training workflows so results could be compared, audited, and promoted consistently.

## 6. 能力扩展项目：Agent Knowledge and Document Intelligence System

项目基于：`rag-benchmark-system`

### 6.1 新定位

不再把它作为独立的“RAG benchmark flagship”，而是把它转型成：

`为 agent 提供复杂知识上下文处理能力的文档理解与检索子系统。`

这个定位变化非常重要。它让你的 RAG 项目不再像独立赛道，而变成 agent 能力栈的一部分。

### 6.2 主亮点

- 复杂文档处理
- OCR / layout / table extraction
- retrieval for agent workflows
- citation grounding
- async ingestion and indexing

### 6.3 必做实现点

1. 文档 ingestion
- PDF 支持
- 扫描件支持
- OCR 或 layout parsing 最少一条闭环
- chunking / metadata extraction

2. 检索能力
- 至少 2 套 retrieval pipeline
- rerank
- citation/page grounding
- 面向 agent 调用的 retrieval API

3. 评测
- answer correctness
- citation accuracy
- page grounding
- latency / cost

4. 与 agent / 平台集成
- 提供给 agent 的 knowledge retrieval 接口
- 评测结果接入 `EvalOps Platform`
- 文档 bad cases 可在平台查看

### 6.4 不做的内容

- 不做通用聊天机器人
- 不做过深前端产品化
- 不做太多无关 benchmark 扩展
- 不做所有多模态模型的横向大比拼

### 6.5 这个项目最后要能回答的问题

- agent 为什么需要专门的 knowledge subsystem
- 复杂文档与纯文本 RAG 的核心区别是什么
- citation 和 grounding 为什么比普通 QA 指标更重要
- ingestion pipeline 如何处理批量文档与增量更新

### 6.6 简历表达目标

- Built a document intelligence subsystem for agents, covering PDF ingestion, OCR/layout-aware parsing, retrieval, reranking, and citation grounding.
- Designed async ingestion and evaluation workflows for document-heavy agent tasks with explicit tradeoffs across quality, latency, and cost.

## 7. 补充项目：Targeted Post-Training and Inference Benchmark

项目基于：`coding-llm-finetune`

### 7.1 新定位

这个项目不再扩展成“大训练平台”，而是收敛成：

`针对 agent 失败模式的 targeted post-training 与 deployment-aware benchmark 项目。`

这里的关键变化是：让它直接服务主线，而不是独立成另一个大方向。

### 7.2 主亮点

- failure-driven data construction
- targeted SFT / DPO
- execution-driven preference pairs
- inference benchmark for deployment tradeoffs

### 7.3 必做实现点

1. 失败样本闭环
- 从 agent 项目抽取失败模式
- 分类 failure patterns
- 生成 targeted data

2. 训练与评测标准化
- dataset version
- config version
- automatic eval outputs
- artifact naming 统一

3. 部署性能对比
- 至少 2 个 serving / quantization 方案对比
- 吞吐、延迟、显存
- 与效果分数联合展示

4. 与平台集成
- eval run 接入 `EvalOps Platform`
- failure cases 与 agent run 关联

### 7.4 不做的内容

- 不做大规模训练调度平台
- 不继续无限扩 SFT/DPO 变种
- 不单纯为了 benchmark score 再打很多 ablation

### 7.5 这个项目最后要能回答的问题

- targeted data 为什么比 generic data 更有针对性
- execution-driven DPO 为什么适合 coding / agent failure
- 为什么部署性能必须和效果一起展示

### 7.6 简历表达目标

- Built a targeted post-training workflow driven by real agent failure cases, using execution-based signals for SFT/DPO data construction and evaluation.
- Benchmarked deployment-oriented model variants across quality, latency, throughput, and memory instead of optimizing benchmark score in isolation.

## 8. 这次真正要补的“大规模工程实践”信号

你要补的不是“真有海量用户”，而是让面试官看到你在设计时有规模意识。

这次所有项目都要围绕下面这些信号展开：

1. 异步任务编排
- API submit
- queue
- worker
- retry
- cancel
- resume

2. 持久化状态
- run state
- step state
- artifact metadata
- failure reason

3. 结构化观测
- request / run id
- latency
- error rate
- token cost
- queue wait time
- success rate

4. 版本化
- dataset version
- prompt/config version
- model version
- release tag

5. 对比与 gating
- compare runs
- threshold-based release
- regression detection

这些能力里，最关键的 3 个是：

- persistent execution
- async orchestration
- eval + observability

如果这些没有做出来，就算是 agent 项目，也很难真正体现工程深度。

## 9. 更新后的执行顺序

这次执行顺序也要跟着改，不再是先做 RAG。

### Phase 1: 先把 Agent 主旗舰做出来
时间：第 1 到 3 周

项目：`llm-coding-agent-system`

目标：

- 重构 execution model
- 加 persistent run state
- 加 resume / retry / audit trail
- 提供 API 入口
- 输出第一版 agent runtime 架构图

为什么先做这个：

- 现在 agent 是主叙事，必须最先成型
- 后续平台要围绕它的 run model 来设计

### Phase 2: 搭建 Agent EvalOps Platform
时间：第 4 到 5 周

项目：新 repo

目标：

- API + queue + worker
- metadata store
- run tracking
- compare 页面
- 先接入 agent

为什么第二步做这个：

- 这是把 agent 从“有系统”变成“有平台和闭环”的关键一步

### Phase 3: 把 RAG 改成 Agent Knowledge Subsystem
时间：第 6 到 7 周

项目：`rag-benchmark-system`

目标：

- 文档 ingestion MVP
- OCR/layout-aware pipeline 最少一条
- retrieval API 化
- 接入 agent 和平台

为什么第三步做这个：

- 这样 RAG 就不是孤立项目，而是 agent 的知识扩展能力

### Phase 4: 收敛升级 Finetune
时间：第 8 周

项目：`coding-llm-finetune`

目标：

- 把失败样本和 agent 联系起来
- 做 inference benchmark
- 统一结果上报

为什么最后做这个：

- 它是加分项，不是市场上最核心的主卖点

### Phase 5: 统一包装
时间：第 9 周

目标：

- 统一 README 风格
- 统一架构图风格
- 给每个项目补性能和结果摘要
- 写简历 bullet
- 准备面试口述

## 10. 每个项目的最小可交付版本

### 10.1 Agent Runtime MVP

- API 提交任务
- 持久化 run state
- pause / resume
- tool trace 存储
- verification result 记录
- run summary 页面或 API

### 10.2 EvalOps MVP

- job submission API
- worker 执行
- metadata store
- run compare
- release gate

### 10.3 Knowledge Subsystem MVP

- PDF ingestion
- OCR 或 layout-aware parsing
- retrieval API
- citation output
- quality / latency report

### 10.4 Post-Training MVP

- failure-driven data pipeline
- 自动评测
- 2 个部署方案 benchmark
- 结果接入平台

## 11. 明确砍掉的内容

为了保证亮点集中，这些内容明确不做：

- 不做第二个新的全新业务项目
- 不做重前端 agent 产品
- 不做大而全训练平台
- 不在每个 repo 重复造 infra
- 不做不服务主线的 random AI demo

## 12. 最终对外叙事

面试时应该这样讲：

1. 我把一个 coding agent 原型升级成了可恢复的 agent runtime，支持任务持久化、工具调用、验证与审计。
2. 我做了一个专门面向 agent 系统的 eval 和 observability 平台，用于任务编排、结果追踪、回归检测和 release gate。
3. 我把原来的 RAG 工作改造成 agent 的文档理解与检索子系统，解决复杂知识输入问题。
4. 我把 post-training 工作收敛成 failure-driven 的 targeted optimization，直接服务 agent 失败模式修复，并补上部署性能 benchmark。

这套组合的优势在于：

- 市场热点明确：agent
- 工程信号明确：runtime + platform + observability
- 差异化明确：knowledge subsystem + failure-driven model optimization
- 不会显得是 4 个互不相干的项目

## 13. 一句话结论

新的最优策略不是“把 Agent 也做一做”，而是：

`把 Agent Runtime 做成主旗舰，用 EvalOps Platform 证明工程深度，用 RAG 子系统证明真实知识处理能力，用 Finetune 项目证明你能闭环修系统失败模式。`

这版计划比上一版更贴市场，也更容易做出真正有亮点的作品集。
