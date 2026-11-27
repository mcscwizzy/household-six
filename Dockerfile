FROM python:3.12.8-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 APP_PORT=3000 DATA_DIR=/app/data
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts
RUN mkdir -p /app/data /app/backups && chown -R app:app /app
USER app
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:3000/api/health', timeout=2)"]
CMD ["python", "-m", "app.server"]
