# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.11-slim AS builder

# Copy the uv binary from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install build dependencies AND python headers (python3-dev fixes the hnswlib error)
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     python3-dev     curl     git     && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a virtual environment and put it in the PATH
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy local dependency first to avoid "Distribution not found" error
COPY nano-graphrag ./nano-graphrag

# Install dependencies into the virtual environment using uv
COPY requirements.txt .
RUN uv pip install --no-cache -r requirements.txt

# ==========================================
# Stage 2: Final Production Image
# ==========================================
FROM python:3.11-slim

# Create a non-root user for security
RUN useradd -m -s /bin/bash apiuser

# Copy the pre-built virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Ensure our container uses the virtual environment's Python
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy the actual application code
COPY . .

# Setup data directory and assign ownership to our non-root user
RUN mkdir -p /data && chown -R apiuser:apiuser /data /app
ENV DATA_ROOT=/data

# Switch to the non-root user
USER apiuser

EXPOSE 8000

# uvicorn[standard] already pulls in uvloop + httptools for best async/HTTP performance.
# --timeout-keep-alive 75: keep HTTP/1.1 connections alive longer (GCP LB expects >60s).
# --workers 1: single process intentional — in-memory progress state must stay in-process.
#   Scale horizontally via Cloud Run instances, not workers, until progress is moved to DB.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--timeout-keep-alive", "75"]

# ---------------------------------------------------------------------------
# Recommended Cloud Run deploy command (run from src/api/):
#
#   gcloud run deploy dashrag-api \
#     --source . \
#     --region us-central1 \
#     --allow-unauthenticated \
#     --cpu 2 \
#     --memory 4Gi \
#     --min-instances 1 \
#     --concurrency 20 \
#     --timeout 3600 \
#     --no-cpu-throttling \
#     --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,DATABASE_URL=database-url:latest,JWT_SECRET_KEY=jwt-secret-key:latest"
#
# IMPORTANT: JWT_SECRET_KEY must be stored in Cloud Secret Manager so it persists
# across redeployments. Without it, every deploy generates a new runtime value,
# invalidating all existing user tokens and forcing everyone to log in again.
#
# One-time setup (create the secret):
#   openssl rand -base64 32 | gcloud secrets create jwt-secret-key --data-file=-
#
# Key flags explained:
#   --no-cpu-throttling   CPU stays allocated during background GraphRAG tasks (202 responses)
#   --min-instances 1     Eliminates cold starts (~10-15s startup for heavy imports)
#   --cpu 2               Two vCPUs for entity extraction / community clustering
#   --concurrency 20      Lower than default 80 to limit memory pressure from concurrent graphs
# ---------------------------------------------------------------------------

#    gcloud run deploy dashrag-api      --source .      --region us-central1      --allow-unauthenticated      --cpu 4      --memory 8Gi      --min-instances 1      --concurrency 20      --timeout 3600      --no-cpu-throttling       --port=8000 --execution-environment gen2   --add-volume=name=data-volume,type=cloud-storage,bucket=dashrag-data-blogv2-457513   --add-volume-mount=volume=data-volume,mount-path=/data   --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,DATABASE_URL=database-url:latest,HF_TOKEN=hf-token:latest,JWT_SECRET_KEY=jwt-secret-key:latest" 