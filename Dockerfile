# Dockerfile - explicit venv paths to avoid "uvicorn: not found"
FROM python:3.11-slim

LABEL org.opencontainers.image.source="your-repo"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VENV_PATH="/venv" \
    PATH="/venv/bin:$PATH" \
    PORT=10000

# Create a non-root user
RUN groupadd -g 1000 appuser || true && \
    useradd -u 1000 -g 1000 -m -s /bin/bash appuser

WORKDIR /srv/app

# Install minimal build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl ca-certificates git && \
    rm -rf /var/lib/apt/lists/*

# Create venv
RUN python -m venv ${VENV_PATH}

# Copy requirements first for Docker cache
COPY requirements.txt /srv/app/requirements.txt

# Use the venv pip explicitly
RUN ${VENV_PATH}/bin/pip install --upgrade pip setuptools wheel && \
    ${VENV_PATH}/bin/pip install --no-cache-dir -r /srv/app/requirements.txt

# Copy app
COPY . /srv/app

# Ensure ownership
RUN chown -R appuser:appuser /srv/app

# Switch user
USER appuser

# Expose port
EXPOSE ${PORT}

# Healthcheck (adjust if your app has different health path)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://127.0.0.1:${PORT}/health || exit 1

# Start command: use explicit venv python to run uvicorn so PATH issues won't break it.
# Accepts GCP_SA_JSON_BASE64 or raw GCP_SA_JSON env var for credentials.
CMD ["bash", "-lc", "\
  set -euo pipefail; \
  if [ -n \"${GCP_SA_JSON_BASE64:-}\" ]; then \
    echo \"$GCP_SA_JSON_BASE64\" | base64 -d > /tmp/gcp_service_account.json && export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_service_account.json; \
  elif [ -n \"${GCP_SA_JSON:-}\" ]; then \
    echo \"$GCP_SA_JSON\" > /tmp/gcp_service_account.json && export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_service_account.json; \
  fi; \
  exec /venv/bin/python -m uvicorn app.main_crewai:app --host 0.0.0.0 --port ${PORT} --proxy-headers \
"]
