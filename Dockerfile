# Production-style container for the FastAPI HR Policy Chatbot.
FROM python:3.12-slim

WORKDIR /app

# System deps for Docling / PDF parsing.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini ./

RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000

CMD ["uvicorn", "hr_chatbot.main:app", "--host", "0.0.0.0", "--port", "8000"]
