#!/usr/bin/env python3
"""Create a deterministic, no-model RAG + EvalOps review fixture."""
from __future__ import annotations

import os
import time
import urllib.request
from io import BytesIO

from fpdf import FPDF

RAG_URL = os.environ.get("RAG_URL", "http://localhost:8080")
EVALOPS_URL = os.environ.get("EVALOPS_URL", "http://localhost:8000")
API_TOKEN = os.environ.get("PORTFOLIO_API_TOKEN", "")


def request(path: str, *, body: bytes | None = None, content_type: str = "application/json") -> dict:
    req = urllib.request.Request(EVALOPS_URL + path, data=body, method="POST" if body else "GET")
    if body:
        req.add_header("Content-Type", content_type)
    if API_TOKEN:
        req.add_header("Authorization", f"Bearer {API_TOKEN}")
    with urllib.request.urlopen(req, timeout=15) as response:
        import json
        return json.loads(response.read())


def make_pdf() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 8, "Portfolio Release Manual\nA candidate is promoted when all required release gate rules pass.")
    return bytes(pdf.output())


def main() -> None:
    boundary = "demo-boundary"
    payload = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"index_id\"\r\n\r\ndemo\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"release-manual.pdf\"\r\n"
        "Content-Type: application/pdf\r\n\r\n"
    ).encode() + make_pdf() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(RAG_URL + "/v1/ingest", data=payload, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    if API_TOKEN:
        req.add_header("Authorization", f"Bearer {API_TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as response:
        import json
        job_id = json.loads(response.read())["job_id"]
    for _ in range(100):
        poll_request = urllib.request.Request(RAG_URL + f"/v1/ingest/{job_id}")
        if API_TOKEN:
            poll_request.add_header("Authorization", f"Bearer {API_TOKEN}")
        with urllib.request.urlopen(poll_request, timeout=5) as response:
            import json
            if json.loads(response.read())["status"] == "completed":
                break
        time.sleep(0.2)
    else:
        raise RuntimeError("demo RAG ingestion did not complete")

    import json
    base = {"schema_version":"rag/v1","dataset":"demo-suite","retriever_mode":"bm25","generator_model":"fixture","num_queries":2,"em":0.5,"f1":0.6,"recall_at_k":0.75,"hallucination_rate":0.1,"avg_retrieval_latency_ms":5,"avg_rerank_latency_ms":0,"avg_generation_latency_ms":0,"avg_query_expansion_latency_ms":0}
    for run_id, f1, hallucination in [("demo-rag-baseline", 0.6, 0.1), ("demo-rag-candidate", 0.75, 0.05)]:
        request("/v1/ingest/rag/v1", body=json.dumps({**base, "run_id":run_id, "f1":f1, "hallucination_rate":hallucination}).encode())
    for _ in range(50):
        if request("/v1/runs?app_type=rag")["total"] >= 2:
            break
        time.sleep(0.2)
    compare = request("/v1/compare", body=json.dumps({"app_type":"rag","baseline_run_id":"demo-rag-baseline","candidate_run_id":"demo-rag-candidate"}).encode())
    request("/v1/gate", body=json.dumps({"compare_session_id":compare["compare_session_id"],"rules":[{"metric":"f1","op":"gte","threshold":0.7},{"metric":"hallucination_rate","op":"lte","threshold":0.08}]}).encode())
    request("/v1/runs/rag/demo-rag-candidate/bad-cases", body=json.dumps({"case_id":"demo-case-1","tag":"citation-review","note":"Seeded review example."}).encode())
    print("DEMO_SEED=passed")


if __name__ == "__main__":
    main()
