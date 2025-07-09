FROM python:3.10 AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN python -m venv .venv
COPY pyproject.toml ./
RUN .venv/bin/pip install .

FROM python:3.10-slim

WORKDIR /app
COPY --from=builder /app/.venv .venv/
COPY . .

# Adiciona o virtualenv ao PATH para o uvicorn ser encontrado
ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
