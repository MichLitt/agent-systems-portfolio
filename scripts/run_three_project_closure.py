#!/usr/bin/env python3
"""Run the local RAG -> Agent -> EvalOps closure without external services."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx
from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
RAG_ROOT = ROOT / "rag-benchmark-system"
AGENT_ROOT = ROOT / "llm-coding-agent-system"
EVALOPS_ROOT = ROOT / "llm-evalops-platform"

# Import the real producer schemas/clients and Agent tool from their projects.
sys.path.insert(0, str(RAG_ROOT))
from src.evalops.client import EvalOpsClient as RagEvalOpsClient  # noqa: E402
from src.evalops.schema import EvalRunReport  # noqa: E402

sys.path.insert(0, str(AGENT_ROOT))
from coder_agent.evalops.client import EvalOpsClient as AgentEvalOpsClient  # noqa: E402
from coder_agent.evalops.schema import AgentRunReport  # noqa: E402
from coder_agent.tools.knowledge_retrieval import KnowledgeRetrievalTool  # noqa: E402


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(client: httpx.Client, url: str, process: subprocess.Popen, timeout: float = 20) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"service exited early with code {process.returncode}: {url}")
        try:
            response = client.get(url)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    raise TimeoutError(f"service did not become healthy: {url}")


def _wait_for_run(
    client: httpx.Client,
    evalops_url: str,
    app_type: str,
    run_id: str,
    timeout: float = 10,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    url = f"{evalops_url}/v1/runs/{app_type}/{run_id}"
    while time.monotonic() < deadline:
        response = client.get(url)
        if response.status_code == 200:
            return response.json()
        if response.status_code != 404:
            response.raise_for_status()
        time.sleep(0.1)
    raise TimeoutError(f"normalized run did not appear: {app_type}/{run_id}")


def _make_pdf(path: Path) -> None:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)
    pages = [
        "Release Gate Manual\nA release gate compares a baseline run with a candidate run. ",
        "Operations\nThe candidate is promoted when every required quality rule passes. ",
    ]
    for text in pages:
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        for line in text.splitlines():
            pdf.multi_cell(0, 8, text=line, new_x="LMARGIN", new_y="NEXT")
    pdf.output(str(path))


def _post_compare_and_gate(
    client: httpx.Client,
    evalops_url: str,
    *,
    app_type: str,
    baseline_run_id: str,
    candidate_run_id: str,
    rules: list[dict[str, Any]],
) -> dict[str, Any]:
    compare = client.post(
        f"{evalops_url}/v1/compare",
        json={
            "app_type": app_type,
            "baseline_run_id": baseline_run_id,
            "candidate_run_id": candidate_run_id,
        },
    )
    compare.raise_for_status()
    gate = client.post(
        f"{evalops_url}/v1/gate",
        json={
            "compare_session_id": compare.json()["compare_session_id"],
            "rules": rules,
        },
    )
    gate.raise_for_status()
    return gate.json()


def _terminate(processes: list[subprocess.Popen]) -> None:
    for process in reversed(processes):
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 5
    for process in reversed(processes):
        if process.poll() is None:
            try:
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)


def run(output_path: Path) -> dict[str, Any]:
    processes: list[subprocess.Popen] = []
    logs: list[tuple[str, Path]] = []

    with tempfile.TemporaryDirectory(prefix="three-project-closure-") as tmp_name, ExitStack() as stack:
        tmp = Path(tmp_name)
        evalops_port = _free_port()
        rag_port = _free_port()
        evalops_url = f"http://127.0.0.1:{evalops_port}"
        rag_url = f"http://127.0.0.1:{rag_port}"
        database_path = tmp / "evalops.db"
        api_token = "closure-token"

        evalops_env = os.environ.copy()
        evalops_env.update(
            {
                "PYTHONPATH": str(EVALOPS_ROOT / "src"),
                "DATABASE_URL": str(database_path),
                "API_HOST": "127.0.0.1",
                "API_PORT": str(evalops_port),
                "WORKER_POLL_INTERVAL_SECS": "1",
                "EVALOPS_API_TOKEN": api_token,
            }
        )

        def start(name: str, command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.Popen:
            log_path = tmp / f"{name}.log"
            log_handle = stack.enter_context(log_path.open("w+", encoding="utf-8"))
            process = subprocess.Popen(
                command,
                cwd=cwd,
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
            processes.append(process)
            logs.append((name, log_path))
            return process

        evalops_python = str(EVALOPS_ROOT / ".venv/bin/python")
        evalops_api = start(
            "evalops-api",
            [evalops_python, str(EVALOPS_ROOT / "scripts/start_api.py")],
            cwd=EVALOPS_ROOT,
            env=evalops_env,
        )
        start(
            "evalops-worker",
            [evalops_python, str(EVALOPS_ROOT / "scripts/start_worker.py")],
            cwd=EVALOPS_ROOT,
            env=evalops_env,
        )

        rag_python = str(RAG_ROOT / ".venv/bin/python")
        rag_data_dir = tmp / "data/indexes"
        rag_env = os.environ.copy()
        rag_env["RAG_API_TOKEN"] = api_token
        rag_api = start(
            "rag-api",
            [
                rag_python,
                str(RAG_ROOT / "scripts/start_api.py"),
                "--host",
                "127.0.0.1",
                "--port",
                str(rag_port),
                "--data-dir",
                str(rag_data_dir),
                "--log-level",
                "warning",
            ],
            cwd=tmp,
            env=rag_env,
        )
        start(
            "rag-ingest-worker",
            [
                rag_python,
                str(RAG_ROOT / "scripts/start_ingest_worker.py"),
                "--data-dir",
                str(rag_data_dir),
                "--poll-seconds",
                "0.05",
            ],
            cwd=tmp,
            env=rag_env,
        )

        try:
            with httpx.Client(timeout=10.0, headers={"Authorization": f"Bearer {api_token}"}) as client:
                _wait_for_health(client, f"{evalops_url}/health", evalops_api)
                _wait_for_health(client, f"{rag_url}/v1/health", rag_api)

                with httpx.Client(timeout=10.0) as anonymous:
                    if anonymous.get(f"{evalops_url}/v1/runs").status_code != 401:
                        raise AssertionError("EvalOps API accepted an unauthenticated request")
                    if anonymous.post(f"{rag_url}/v1/retrieve", json={}).status_code != 401:
                        raise AssertionError("RAG API accepted an unauthenticated request")

                pdf_path = tmp / "closure.pdf"
                _make_pdf(pdf_path)
                with pdf_path.open("rb") as pdf_file:
                    ingest = client.post(
                        f"{rag_url}/v1/ingest",
                        data={"index_id": "closure", "parser": "pdf"},
                        files={"file": (pdf_path.name, pdf_file, "application/pdf")},
                        timeout=30.0,
                    )
                ingest.raise_for_status()
                job_id = ingest.json()["job_id"]

                deadline = time.monotonic() + 20
                job: dict[str, Any] = {}
                while time.monotonic() < deadline:
                    job_response = client.get(f"{rag_url}/v1/ingest/{job_id}")
                    job_response.raise_for_status()
                    job = job_response.json()
                    if job["status"] in {"completed", "failed"}:
                        break
                    time.sleep(0.1)
                if job.get("status") != "completed":
                    raise RuntimeError(f"RAG ingest did not complete: {job}")

                tool_output = asyncio.run(
                    KnowledgeRetrievalTool(base_url=rag_url, api_token=api_token).execute(
                        query="When is a candidate promoted?",
                        index_id="closure",
                        top_k=3,
                    )
                )
                if "closure.pdf" not in tool_output or "[p." not in tool_output:
                    raise AssertionError(f"Agent retrieval lacks source/page evidence: {tool_output}")

                rag_endpoint = f"{evalops_url}/v1/ingest/rag/v1"
                rag_baseline = EvalRunReport(
                    run_id="closure-rag-baseline",
                    dataset="closure-suite",
                    retriever_mode="bm25-v1",
                    generator_model="extractive-fixture",
                    num_queries=2,
                    em=0.60,
                    f1=0.65,
                    recall_at_k=0.80,
                    hallucination_rate=0.10,
                    avg_retrieval_latency_ms=5.0,
                )
                rag_candidate = EvalRunReport(
                    **{
                        **asdict(rag_baseline),
                        "run_id": "closure-rag-candidate",
                        "retriever_mode": "bm25-v2",
                        "em": 0.68,
                        "f1": 0.72,
                        "recall_at_k": 0.90,
                        "hallucination_rate": 0.05,
                    }
                )
                RagEvalOpsClient(endpoint=rag_endpoint, api_key=api_token)._do_submit(rag_baseline)
                RagEvalOpsClient(endpoint=rag_endpoint, api_key=api_token)._do_submit(rag_candidate)

                agent_endpoint = f"{evalops_url}/v1/ingest/agent/v1"
                agent_baseline = AgentRunReport(
                    run_id="closure-agent-baseline",
                    run_type="eval",
                    status="success",
                    total_steps=6,
                    total_tool_calls=5,
                    tool_success_rate=0.80,
                    total_tokens=1200,
                    wall_duration_ms=1500,
                    preset="closure",
                    llm_profile="fixture",
                    benchmark_name="closure-suite",
                    task_ids=["retrieve-manual"],
                )
                agent_candidate = AgentRunReport(
                    **{
                        **asdict(agent_baseline),
                        "run_id": "closure-agent-candidate",
                        "total_steps": 5,
                        "tool_success_rate": 1.0,
                        "total_tokens": 1100,
                        "wall_duration_ms": 1300,
                    }
                )
                AgentEvalOpsClient(endpoint=agent_endpoint, api_key=api_token)._do_submit(agent_baseline)
                AgentEvalOpsClient(endpoint=agent_endpoint, api_key=api_token)._do_submit(agent_candidate)

                for app_type, run_id in [
                    ("rag", rag_baseline.run_id),
                    ("rag", rag_candidate.run_id),
                    ("agent", agent_baseline.run_id),
                    ("agent", agent_candidate.run_id),
                ]:
                    _wait_for_run(client, evalops_url, app_type, run_id)

                rag_gate = _post_compare_and_gate(
                    client,
                    evalops_url,
                    app_type="rag",
                    baseline_run_id=rag_baseline.run_id,
                    candidate_run_id=rag_candidate.run_id,
                    rules=[
                        {"metric": "f1", "op": "gte", "threshold": 0.70},
                        {"metric": "f1", "op": "delta_abs_gte", "threshold": 0.05},
                        {"metric": "hallucination_rate", "op": "lte", "threshold": 0.08},
                    ],
                )
                agent_gate = _post_compare_and_gate(
                    client,
                    evalops_url,
                    app_type="agent",
                    baseline_run_id=agent_baseline.run_id,
                    candidate_run_id=agent_candidate.run_id,
                    rules=[
                        {"metric": "tool_success_rate", "op": "gte", "threshold": 0.95},
                        {
                            "metric": "tool_success_rate",
                            "op": "delta_abs_gte",
                            "threshold": 0.10,
                        },
                    ],
                )

                if rag_gate["decision"] != "promoted" or agent_gate["decision"] != "promoted":
                    raise AssertionError(f"release gate rejected closure: {rag_gate}, {agent_gate}")

                with sqlite3.connect(database_path) as conn:
                    persisted_decisions = conn.execute(
                        "SELECT COUNT(*) FROM release_decisions WHERE decision='promoted'"
                    ).fetchone()[0]
                if persisted_decisions != 2:
                    raise AssertionError(
                        f"expected two persisted promoted decisions, got {persisted_decisions}"
                    )

                summary = {
                    "rag_ingest": "passed",
                    "agent_retrieval": "passed",
                    "rag_evalops_gate": rag_gate["decision"],
                    "agent_evalops_gate": agent_gate["decision"],
                    "security_smoke": "passed",
                    "persisted_release_decisions": persisted_decisions,
                    "three_project_closure": "passed",
                }
        except Exception as exc:
            diagnostics = []
            for name, log_path in logs:
                if log_path.exists():
                    diagnostics.append(f"--- {name} ---\n{log_path.read_text(encoding='utf-8')[-4000:]}")
            raise RuntimeError(f"three-project closure failed: {exc}\n" + "\n".join(diagnostics)) from exc
        finally:
            _terminate(processes)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "artifacts/closure/three-project-closure-latest.json",
    )
    args = parser.parse_args()
    summary = run(args.output.resolve())

    print(f"RAG_INGEST={summary['rag_ingest']}")
    print(f"AGENT_RETRIEVAL={summary['agent_retrieval']}")
    print(f"RAG_EVALOPS_GATE={summary['rag_evalops_gate']}")
    print(f"AGENT_EVALOPS_GATE={summary['agent_evalops_gate']}")
    print(f"THREE_PROJECT_CLOSURE={summary['three_project_closure']}")
    print(f"SUMMARY={args.output.resolve()}")


if __name__ == "__main__":
    main()
