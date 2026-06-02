FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "cortexbrain.main:app", "--host", "0.0.0.0", "--port", "8000"]
