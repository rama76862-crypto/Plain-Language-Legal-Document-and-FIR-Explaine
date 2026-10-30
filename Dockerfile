FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    INFERENCE_MODE=hosted ML_MODE=real ML_EMBEDDINGS=off ML_TRANSLATOR=qwen \
    ML_GENERATION_PROFILE=concise OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
    EXTRACTION_WORKERS=1 EXTRACTION_MEMORY_MB=768 OCR_MAX_PIXELS=4000000 \
    WEB_DIST_DIR=/app/frontend/dist RUNTIME_DIR=/app/work/runtime/server \
    PORT=8080 WEB_ORIGIN=http://localhost:8080 MODEL_TIMEOUT_SECONDS=60
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-hin tesseract-ocr-pan && rm -rf /var/lib/apt/lists/*
COPY requirements.hosted.txt ./
RUN pip install --no-cache-dir -r requirements.hosted.txt
COPY apps/ ./apps/
COPY --from=frontend /build/dist ./frontend/dist
RUN useradd --create-home --uid 10001 appuser && mkdir -p /app/work/runtime && chown -R appuser:appuser /app/work
USER appuser
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import os; from urllib.request import urlopen; urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/api/v1/health',timeout=4)"
CMD ["python","-m","apps.deploy"]
