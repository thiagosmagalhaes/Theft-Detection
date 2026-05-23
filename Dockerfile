# syntax=docker/dockerfile:1.4
# Multi-stage build for Theft Detection Backend
FROM python:3.10-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies required for OpenCV and compiled Python packages
RUN apt-get update && apt-get install -y \
    g++ \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy Docker-specific requirements file
COPY requirements.docker.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.docker.txt

# Production stage
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/ ./backend/
COPY main.py .
COPY cameras.json .
COPY settings.json .

# Use local YOLO models when available; download only if missing in project folder
ARG YOLO_OBJ_MODEL_URL=https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26x.pt
ARG YOLO_POSE_MODEL_URL=https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26x-pose.pt
RUN --mount=type=bind,source=.,target=/src,readonly \
    python -c "import os, shutil, urllib.request; models=[('yolo26x.pt','${YOLO_OBJ_MODEL_URL}'),('yolo26x-pose.pt','${YOLO_POSE_MODEL_URL}')]; [shutil.copyfile('/src/'+name, name) if os.path.exists('/src/'+name) else urllib.request.urlretrieve(url, name) for name, url in models]"

# Create necessary directories
RUN mkdir -p alerts faces faces/detections

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV YOLO_OBJ_MODEL=yolo26x.pt
ENV YOLO_POSE_MODEL=yolo26x-pose.pt

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/settings')" || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
