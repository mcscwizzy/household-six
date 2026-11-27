FROM python:3.12.8-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_PORT=3000 DATA_DIR=/app/data BIND_ADDRESS=0.0.0.0
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
ARG WITH_MCP=0
ARG WITH_LOCAL_OCR=0
COPY requirements.lock requirements-optional.lock ./
RUN if [ "$WITH_MCP" = 1 ]; then lock=requirements-optional.lock; else lock=requirements.lock; fi && \
    pip install --no-cache-dir --require-hashes -r "$lock"
RUN if [ "$WITH_LOCAL_OCR" = 1 ]; then \
    apt-get update && apt-get install -y --no-install-recommends tesseract-ocr poppler-utils && \
    rm -rf /var/lib/apt/lists/*; fi
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
RUN mkdir -p /app/data /app/backups && chown -R app:app /app
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/api/health', timeout=2)"]
CMD ["python", "-m", "app.server"]
