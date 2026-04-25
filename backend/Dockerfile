FROM python:3.12-slim AS base

WORKDIR /app

# System deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Install pip tooling
RUN pip install --no-cache-dir hatch

# Copy project metadata first (layer cache)
COPY pyproject.toml README.md ./
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Install application + deps
RUN pip install --no-cache-dir -e .

EXPOSE 8000

# Default: API server. Override in docker-compose for the worker.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]