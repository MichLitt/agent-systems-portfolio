FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv
WORKDIR /app
COPY rag-benchmark-system/pyproject.toml rag-benchmark-system/uv.lock ./
RUN uv sync --frozen --no-dev
COPY rag-benchmark-system/ ./
RUN mkdir -p /data/indexes
