FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY rag-benchmark-system/pyproject.toml rag-benchmark-system/uv.lock ./
RUN uv sync --frozen --no-dev
COPY rag-benchmark-system/ ./
COPY scripts/seed_demo.py /demo/seed_demo.py
CMD ["uv", "run", "python", "/demo/seed_demo.py"]
