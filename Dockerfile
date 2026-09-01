# DJ AI OS — Multi-stage Docker build
# Stage 1: Build React admin SPA
# Stage 2: Python API server

# ─── Stage 1: Admin SPA ───
FROM node:20-alpine AS admin-build

WORKDIR /admin
COPY admin/package*.json ./
RUN npm install
COPY admin/ ./
RUN npm run build

# ─── Stage 2: Python API ───
FROM python:3.12-slim AS api

WORKDIR /app

# System deps for API (ffmpeg for yt-dlp, libsndfile for audio metadata)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt

COPY app/ ./app/
COPY tools/ ./tools/
COPY alembic.ini ./
# Copy built admin SPA from stage 1
COPY --from=admin-build /admin/build ./admin/build

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Use shell form so $PORT from Render is respected; fallback to 8000 for local dev
CMD ["sh", "-c", "uvicorn app.server.run:app --host 0.0.0.0 --port ${PORT:-8000}"]
