# =============================================================================
# AI Resume Matcher — Dockerfile
#
# CPU-only PyTorch:
#   We pass --extra-index-url https://download.pytorch.org/whl/cpu so pip
#   resolves the cpu-only torch wheel (~200 MB) instead of the default CUDA
#   wheel (~2 GB). This keeps the image lean and avoids NVIDIA runtime deps
#   that are never used on Render's CPU-only infrastructure.
# =============================================================================

FROM python:3.10-slim

WORKDIR /app

# System dependencies required for psycopg2 and some ML packages
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies.
# --extra-index-url ensures PyTorch is resolved from the CPU-only index.
# --no-cache-dir keeps the image smaller.
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

# Copy the entire application source
COPY . .

# Render injects $PORT at runtime (default 10000).
# The application also binds correctly on local docker run with -e PORT=8000.
EXPOSE 10000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]
