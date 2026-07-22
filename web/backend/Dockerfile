FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/models/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/models/sentence-transformers \
    FUND_INSIGHT_ROOT=/app \
    FUND_INSIGHT_DATA_DIR=/data

WORKDIR /app
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip \
    && pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r /tmp/requirements.txt
COPY backend /app/backend
COPY config /app/config

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
