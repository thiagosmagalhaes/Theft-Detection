#!/bin/bash

# Theft Detection System - Docker Quick Start Script
# This script builds and starts all containers

echo "🚀 Starting Theft Detection System with Docker..."
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if required files exist
echo "📋 Checking required files..."
pose_model="yolov8n-pose.pt"
obj_model="yolov8n.pt"

if [ -f ".env" ]; then
    env_pose=$(grep -E '^YOLO_POSE_MODEL=' .env | tail -n 1 | cut -d '=' -f 2-)
    env_obj=$(grep -E '^YOLO_OBJ_MODEL=' .env | tail -n 1 | cut -d '=' -f 2-)

    if [ -n "$env_pose" ]; then
        pose_model=$(echo "$env_pose" | sed -e "s/^'//" -e "s/'$//" -e 's/^"//' -e 's/"$//')
    fi
    if [ -n "$env_obj" ]; then
        obj_model=$(echo "$env_obj" | sed -e "s/^'//" -e "s/'$//" -e 's/^"//' -e 's/"$//')
    fi
fi

required_files=("$pose_model" "$obj_model" "cameras.json" "settings.json")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Required file not found: $file"
        exit 1
    fi
    echo "  ✓ $file"
done

# Create required directories
echo ""
echo "📁 Creating required directories..."
mkdir -p alerts faces faces/detections
echo "  ✓ Directories created"

# Build and start containers
echo ""
echo "🔨 Building Docker images..."
docker-compose build

echo ""
echo "▶️  Starting containers..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service status
echo ""
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "✅ Theft Detection System is running!"
echo ""
echo "🌐 Access the services:"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo "   - Dashboard: http://localhost:3000"
echo "   - WebSocket: ws://localhost:8000/ws"
echo ""
echo "📝 Useful commands:"
echo "   - View logs: docker-compose logs -f"
echo "   - Stop system: docker-compose down"
echo "   - Restart: docker-compose restart"
echo ""
