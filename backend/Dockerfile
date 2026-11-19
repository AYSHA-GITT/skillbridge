# SkillBridge API image (Flask + gunicorn). Works on x86_64 and ARM64 (Oracle Ampere).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface

RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# CPU-only PyTorch first, so sentence-transformers doesn't pull the multi-GB CUDA build.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 app \
 && mkdir -p uploads/resumes uploads/avatars uploads/evidence .cache/huggingface \
 && chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

# One process with threads: the embedding model is loaded once, and the in-memory rate
# limiter / login lockout counters are shared by every request.
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "8", \
     "--timeout", "180", "--access-logfile", "-"]
