# Production image for the RecoverAI backend (FastAPI). Deployed to a
# platform like Render; the frontend is deployed separately to Vercel and
# is NOT built from this image. See README §9 for the full deployment guide.
#
# Ollama/Qwen 2.5 3B is intentionally NOT part of this image -- it stays
# local/demo-only (README §5, §9). In production the AI layer is always
# unreachable, and the app falls back to the deterministic recovery engine
# by design (see app/ai/service.py); GET /health reports this as
# "ai_provider": "unavailable" without affecting overall status.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --create-home --shell /usr/sbin/nologin appuser
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# $PORT is injected by the hosting platform (e.g. Render); defaults to
# 8000 for `docker run` without one set.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
