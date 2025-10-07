# Use a small official Python base
FROM python:3.11-slim

# metadata
LABEL org.opencontainers.image.source="your-repo"
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/venv/bin:$PATH" \
    PORT=10000

# create a non-root user for security
RUN groupadd -g 1000 appuser || true && \
    useradd -u 1000 -g 1000 -m -s /bin/bash appuser

WORKDIR /srv/app

# install system dependencies (kept minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Create a venv to isolate packages
RUN python -m venv /venv

# Copy only requirements first to leverage Docker cache
COPY requirements.txt /srv/app/requirements.txt

# Upgrade pip and install python deps into venv; avoid cache to keep image small
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /srv/app/requirements.txt

# Copy application code (use .dockerignore to avoid copying unnecessary files)
COPY . /srv/app

# fix ownership of copied files
RUN chown -R appuser:appuser /srv/app

# switch to non-root user
USER appuser

# Expose port that your app uses (can be overridden by env)
EXPOSE ${PORT}

# Optional healthcheck (simple TCP check to uvi/gunicorn)
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -f http://127.0.0.1:${PORT}/health || exit 1

# Entrypoint: write GCP service account if provided then exec uvicorn
# Important: use exec form so PID 1 is the uvicorn process (signals handled)
CMD ["bash", "-lc", "\
  set -euo pipefail; \
  if [ -n \"${GCP_SA_JSON:-}\" ]; then \
    # prefer raw JSON if available, else base64 may be used in CI/CD; handle both:
    echo \"$GCP_SA_JSON\" > /tmp/gcp_service_account.json && \
    export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_service_account.json; \
  fi; \
  exec uvicorn app.main_crewai:app --host 0.0.0.0 --port ${PORT} --proxy-headers"]
