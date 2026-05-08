# ── Base Image ────────────────────────────────────────────────
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# ── Install dependencies ───────────────────────────────────────
# Copy requirements first (Docker caches this layer — faster rebuilds)
COPY backend/requirements.txt   ./backend/requirements.txt
COPY security/requirements.txt  ./security/requirements.txt
COPY storage/requirements.txt   ./storage/requirements.txt

RUN pip install --no-cache-dir \
    -r backend/requirements.txt \
    -r security/requirements.txt \
    -r storage/requirements.txt

# ── Copy source code ───────────────────────────────────────────
COPY backend/   ./backend/
COPY security/  ./security/
COPY storage/   ./storage/
COPY .env       ./.env

# Make sure Python can find our modules
ENV PYTHONPATH=/app

# ── Run the server ─────────────────────────────────────────────
EXPOSE 5000
CMD ["python", "-m", "backend.app"]