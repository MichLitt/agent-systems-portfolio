# G3 正式对照实验运行指南

本指南用于完成 G3 的正式 `baseline × candidate × 3 seeds` 运行。正式
结果只能来自 GitHub Actions 的 `G3 Formal Trial` workflow；本机桌面会话的
探索性运行不可混入正式证据。

## 一次性准备

1. 将根工程和 EvalOps 子项目的 G3 提交推送到各自的 `main`。
2. 为 GitHub Actions 注册稳定的 self-hosted runner，并添加标签
   `g3-stable`。runner 必须可持续运行至少 90 分钟，具有 Docker/网络访问和
   Python/uv 运行环境。
3. 创建或更新 GitHub Environment：`g3-formal-trial`。
4. 在该 Environment 配置 secret `GLM_5_API_KEY`。不要将密钥写入仓库、日志
   或 workflow 输入。
5. 从 workflow dispatch 页面确认 `G3 Formal Trial` 使用
   `self-hosted, g3-stable` 标签，而不是 GitHub-hosted 或交互桌面 runner。

## 六次冻结运行

对每一个组合手动触发一次 workflow：

| Arm | Seed |
| --- | --- |
| baseline | 101 |
| candidate | 101 |
| baseline | 202 |
| candidate | 202 |
| baseline | 303 |
| candidate | 303 |

每次 workflow 都会：构建固定语料、启动仅绑定本机回环地址的 RAG 服务、运行
20 个任务、在每任务后写 checkpoint，并上传 raw suite artifact。不得在同一个
冻结 trial 内通过修改 timeout、task manifest、RAG index、模型 profile 或重跑
失败任务来改变条件。

## 汇总与发布门禁

六个 raw suite artifact 被放回同一稳定执行环境的
`artifacts/g3-agent-rag-ablation/runs/` 后，运行：

```bash
python3 scripts/build_g3_evidence.py
EVALOPS_ENDPOINT=http://127.0.0.1:8000/v1 \
EVALOPS_API_KEY=<token> \
python3 scripts/ingest_g3_evidence.py
```

证据构建器只接受完整且与 frozen config 一致的六个 suite。随后补充
`docs/reports/agent-rag-ablation-v1.md`，并运行：

```bash
make require-evidence
```

只有 EvalOps gate 返回 `promoted` 时，才能在 README 或简历中使用量化提升
表述。`rejected` 或中性结果仍须作为真实证据保留并报告。
