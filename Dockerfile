# Dockerfile - production-friendly for your InsureAI app
FROM python:3.11-slim

LABEL org.opencontainers.image.source="your-repo"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH" \
    PORT=10000

# Create a non-root user
RUN groupadd -g 1000 appuser || true && \
    useradd -u 1000 -g 1000 -m -s /bin/bash appuser

WORKDIR /srv/app

# Install minimal build deps (remove lists after)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

# Create venv and ensure PATH contains venv bin
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy dependency spec first to leverage Docker cache
COPY requirements.txt /srv/app/requirements.txt

# Upgrade pip and install Python deps into venv
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /srv/app/requirements.txt

# Copy app sources
COPY . /srv/app

# Ensure app files owned by non-root user
RUN chown -R appuser:appuser /srv/app

# Switch to non-root user
USER appuser

# Expose port (allow override with PORT env var)
EXPOSE ${PORT}

# Healthcheck - adjust endpoint if your app uses different path
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://127.0.0.1:${PORT}/health || exit 1

# Start command:
# - Accepts either raw JSON in GCP_SA_JSON or base64-encoded JSON in GCP_SA_JSON_BASE64.
# - Uses `python -m uvicorn` so uvicorn will be found even if installed into venv.
CMD ["bash", "-lc", "\
  set -euo pipefail; \
  if [ -n \"${GCP_SA_JSON_BASE64:-}\" ]; then \
    echo \"Decoding GCP_SA_JSON_BASE64...\"; \
    echo \"$GCP_SA_JSON_BASE64\" | base64 -d > /tmp/gcp_service_account.json && \
    export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_service_account.json; \
  elif [ -n \"${GCP_SA_JSON:-}\" ]; then \
    echo \"Writing raw GCP_SA_JSON...\"; \
    echo \"$GCP_SA_JSON\" > /tmp/gcp_service_account.json && \
    export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_service_account.json; \
  fi; \
  exec python -m uvicorn app.main_crewai:app --host 0.0.0.0 --port ${PORT} --proxy-headers \
"]
