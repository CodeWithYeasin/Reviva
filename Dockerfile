# Reviva — CUDA-ready image (GPU box / self-host).
# For a CPU-only host, use Dockerfile.cpu instead.
#
#   docker build -t reviva .
#   docker run --gpus all -p 8000:8000 reviva

# ---- Stage 1: build the React UI (so the image ships a working frontend) ----
FROM node:20-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: the app ----
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip ffmpeg libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install torch (CUDA) first, then the rest.
RUN pip3 install --no-cache-dir torch==2.3.1 torchvision==0.18.1 \
        --index-url https://download.pytorch.org/whl/cu121

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY --from=web /web/dist ./frontend/dist

EXPOSE 8000
# Process in RAM for true no-disk handling.
ENV REVIVA_WORK_DIR=/dev/shm/reviva
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
