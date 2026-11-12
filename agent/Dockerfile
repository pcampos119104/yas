FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /agent

RUN pip install --no-cache-dir uv==0.13.7

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

RUN useradd --create-home --uid 1000 agent

COPY --chown=agent:agent . .
RUN uv sync --frozen --no-dev

USER agent

CMD ["python", "-m", "agent.main"]
