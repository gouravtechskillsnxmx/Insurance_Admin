# Dockerfile
FROM python:3.11-slim

# system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /srv/app

# copy only requirements first for better caching
COPY requirements.txt /srv/app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r /srv/app/requirements.txt

# copy app code
COPY . /srv/app

# create a non-root user (optional but recommended)
RUN useradd -m appuser && chown -R appuser /srv/app
USER appuser

# Expose the port Render sets via $PORT
ENV PORT=10000
EXPOSE ${PORT}

# Entrypoint: write GOOGLE service account (base64 or raw JSON) into file at start,
# export GOOGLE_APPLICATION_CREDENTIALS, then run uvicorn.
# Render lets you set environment variables; we'll expect GCP_SA_JSON (base64-encoded or raw)
CMD bash -lc '\
  set -e; \
  if [ -n "$GCP_SA_JSON" ]; then \
    echo "$GCP_SA_JSON" > /tmp/gcp_service_account.json && export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_service_account.json; \
  fi; \
  uvicorn app.main_crewai:app --host 0.0.0.0 --port ${PORT} --proxy-headers'
