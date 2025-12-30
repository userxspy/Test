# ==========================================
# ⚡ OPTIMIZED PRODUCTION DOCKERFILE
# Python 3.11 | Fast | Stable | Koyeb-safe
# ==========================================

FROM python:3.10-slim

# ------------------------------
# Runtime Environment Optimizations
# ------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONOPTIMIZE=1 \
    TZ=Asia/Kolkata \
    PIP_NO_CACHE_DIR=1

# ------------------------------
# System dependencies (minimum)
# ------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------
# App directory
# ------------------------------
WORKDIR /Auto-Filter-Bot

# ------------------------------
# Install Python dependencies first (better cache)
# ------------------------------
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ------------------------------
# Copy bot source code
# ------------------------------
COPY . .

# ------------------------------
# Optional: quick runtime sanity check
# ------------------------------
RUN python - <<EOF
import sys
print("Python:", sys.version)
EOF

# ------------------------------
# Start bot
# ------------------------------
CMD ["python", "bot.py"]
