# Theft Detection System - Docker Quick Start Script (PowerShell)
# This script builds and starts all containers.

Write-Host "Starting Theft Detection System with Docker..." -ForegroundColor Cyan
Write-Host ""

# Check if Docker is installed
try {
    docker --version | Out-Null
} catch {
    Write-Host "Docker is not installed. Please install Docker first." -ForegroundColor Red
    exit 1
}

# Check if Docker Compose is installed
try {
    docker compose version | Out-Null
} catch {
    Write-Host "Docker Compose plugin is not installed. Please install Docker Compose first." -ForegroundColor Red
    exit 1
}

# Check if required files exist
Write-Host "Checking required files..." -ForegroundColor Yellow
$poseModel = "yolo26x-pose.pt"
$objModel = "yolo26x.pt"

function Ensure-ModelFile {
    param(
        [Parameter(Mandatory = $true)][string]$ModelFile,
        [string]$ModelUrl
    )

    if (Test-Path $ModelFile) {
        Write-Host "  OK: $ModelFile" -ForegroundColor Green
        return $true
    }

    if ([string]::IsNullOrWhiteSpace($ModelUrl)) {
        return $false
    }

    Write-Host "  Downloading $ModelFile..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $ModelUrl -OutFile $ModelFile
        Write-Host "  OK: Downloaded $ModelFile" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  Failed to download $ModelFile from $ModelUrl" -ForegroundColor Red
        return $false
    }
}

if (Test-Path ".env") {
    $envFile = Get-Content ".env"

    $poseLine = $envFile | Where-Object { $_ -match '^\s*YOLO_POSE_MODEL\s*=' } | Select-Object -First 1
    if ($poseLine) {
        $poseModel = ($poseLine -split '=', 2)[1].Trim().Trim('"').Trim("'")
    }

    $objLine = $envFile | Where-Object { $_ -match '^\s*YOLO_OBJ_MODEL\s*=' } | Select-Object -First 1
    if ($objLine) {
        $objModel = ($objLine -split '=', 2)[1].Trim().Trim('"').Trim("'")
    }
}

$poseUrl = if ($poseModel -eq "yolo26x-pose.pt") { "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26x-pose.pt" } else { "" }
$objUrl = if ($objModel -eq "yolo26x.pt") { "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26x.pt" } else { "" }

if (-not (Ensure-ModelFile -ModelFile $poseModel -ModelUrl $poseUrl)) {
    Write-Host "Required model not found and automatic download is unavailable: $poseModel" -ForegroundColor Red
    exit 1
}

if (-not (Ensure-ModelFile -ModelFile $objModel -ModelUrl $objUrl)) {
    Write-Host "Required model not found and automatic download is unavailable: $objModel" -ForegroundColor Red
    exit 1
}

$requiredFiles = @("cameras.json", "settings.json")
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "Required file not found: $file" -ForegroundColor Red
        exit 1
    }
    Write-Host "  OK: $file" -ForegroundColor Green
}

# Create required directories
Write-Host ""
Write-Host "Creating required directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "alerts" | Out-Null
New-Item -ItemType Directory -Force -Path "faces" | Out-Null
New-Item -ItemType Directory -Force -Path "faces\detections" | Out-Null
Write-Host "  OK: Directories created" -ForegroundColor Green

# Build and start containers
Write-Host ""
Write-Host "Building Docker images..." -ForegroundColor Yellow
docker compose build
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker build failed. Check output above." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Starting containers..." -ForegroundColor Yellow
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "docker compose up failed. Check output above." -ForegroundColor Red
    exit $LASTEXITCODE
}

# Check service status
Write-Host ""
Write-Host "Service status:" -ForegroundColor Cyan
docker compose ps
if ($LASTEXITCODE -ne 0) {
    Write-Host "Could not read service status." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Theft Detection System is running." -ForegroundColor Green
Write-Host ""
Write-Host "Access the services:" -ForegroundColor Cyan
Write-Host "   - Backend API: http://localhost:8000"
Write-Host "   - API Docs: http://localhost:8000/docs"
Write-Host "   - Dashboard: http://localhost:3000"
Write-Host "   - WebSocket: ws://localhost:8000/ws"
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Cyan
Write-Host "   - View logs: docker compose logs -f"
Write-Host "   - Stop system: docker compose down"
Write-Host "   - Restart: docker compose restart"
Write-Host ""
