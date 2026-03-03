# ==========================================
# Stage 1: Build React Frontend
# ==========================================
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

# Install dependencies (leverage docker cache)
COPY frontend/package*.json ./
RUN npm ci

# Copy source and build
COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Build Python FastAPI Backend
# ==========================================
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Copy local edge_node, sim_engine, eval_harness
COPY edge_node/ ./edge_node/
COPY sim_engine/ ./sim_engine/
COPY eval_harness/ ./eval_harness/
COPY verify_*.py ./

# Copy backend api code
COPY backend/ ./backend/

# Copy the built React static files from Stage 1 into the backend container
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Modify backend/main.py at runtime to statically mount the frontend
# We do this here to avoid polluting the pure API code with frontend mounting logic during local dev.
RUN echo "\nfrom fastapi.staticfiles import StaticFiles\napp.mount('/', StaticFiles(directory='frontend/dist', html=True), name='static')" >> backend/main.py

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=8080

EXPOSE 8080

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8080/api/health || exit 1

# Run Uvicorn Server
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips='*'"]
