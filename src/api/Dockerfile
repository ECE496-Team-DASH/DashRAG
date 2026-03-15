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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


gcloud run deploy dashrag-api   --source .   --region us-central1   --allow-unauthenticated   --remove-env-vars="GEMINI_API_KEY,DATABASE_URL"   --set-secrets="GEMINI_API_KEY=gemini-api-key:latest,DATABASE_URL=database-url:latest"