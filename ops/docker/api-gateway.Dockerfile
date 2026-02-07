FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY libs /app/libs
COPY services /app/services
COPY modules /app/modules
COPY apps/api-gateway /app/apps/api-gateway

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

EXPOSE 8080
CMD ["uvicorn", "main:app", "--app-dir", "apps/api-gateway", "--host", "0.0.0.0", "--port", "8080"]
