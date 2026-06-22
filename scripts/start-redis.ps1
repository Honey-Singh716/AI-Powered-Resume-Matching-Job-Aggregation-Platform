# Start Redis for local development (requires Docker Desktop)
docker compose up -d redis

Write-Host "Waiting for Redis to be ready..."
$maxAttempts = 12
for ($i = 1; $i -le $maxAttempts; $i++) {
    try {
        python -c "from services.redis_service import init_redis; import sys; sys.exit(0 if init_redis() else 1)"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Redis is connected at redis://localhost:6379/0"
            exit 0
        }
    } catch {}
    Start-Sleep -Seconds 2
}

Write-Host "Redis container started but connection check failed. Ensure Docker Desktop is running."
exit 1
