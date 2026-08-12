FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY llm-coding-agent-system/pyproject.toml llm-coding-agent-system/uv.lock ./
RUN uv sync --frozen --no-dev
COPY llm-coding-agent-system/ ./
RUN mkdir -p /data/memory /workspace

CMD ["uv", "run", "python", "-m", "coder_agent", "serve", "--host", "0.0.0.0", "--port", "8765"]
