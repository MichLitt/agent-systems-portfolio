FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY llm-evalops-platform/pyproject.toml llm-evalops-platform/uv.lock ./
RUN uv sync --frozen --no-dev
COPY llm-evalops-platform/ ./
RUN mkdir -p /data
