# XiaoZhi Manager API - Development Setup Script
# This script sets up the development environment for the Manager API

Write-Host "🚀 XiaoZhi Manager API Development Setup" -ForegroundColor Green
Write-Host "=======================================" -ForegroundColor Green

# Check if Docker is running
Write-Host "📦 Checking Docker..." -ForegroundColor Yellow
try {
    docker --version | Out-Null
    Write-Host "✅ Docker is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not available. Please install Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Check if Maven is available
Write-Host "🔨 Checking Maven..." -ForegroundColor Yellow
try {
    mvn --version | Out-Null
    Write-Host "✅ Maven is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Maven is not available. Please install Maven and try again." -ForegroundColor Red
    exit 1
}

# Start Docker containers
Write-Host "🐳 Starting Docker containers..." -ForegroundColor Yellow
docker-compose up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker containers started successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to start Docker containers" -ForegroundColor Red
    exit 1
}

# Wait for containers to be healthy
Write-Host "⏳ Waiting for containers to be healthy..." -ForegroundColor Yellow
$timeout = 60
$elapsed = 0
do {
    $status = docker-compose ps --services --filter "status=running" | Measure-Object -Line
    if ($status.Lines -eq 4) {
        Write-Host "✅ All containers are running" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 2
    $elapsed += 2
    Write-Host "." -NoNewline -ForegroundColor Yellow
} while ($elapsed -lt $timeout)

if ($elapsed -ge $timeout) {
    Write-Host "`n⚠️  Containers may still be starting. Check with 'docker-compose ps'" -ForegroundColor Yellow
} else {
    Write-Host ""
}

# Display container status
Write-Host "📋 Container Status:" -ForegroundColor Cyan
docker-compose ps

Write-Host "`n🌐 Service URLs:" -ForegroundColor Cyan
Write-Host "   • API Documentation: http://localhost:8002/xiaozhi/doc.html" -ForegroundColor White
Write-Host "   • Application: http://localhost:8002/toy" -ForegroundColor White
Write-Host "   • phpMyAdmin: http://localhost:8080" -ForegroundColor White
Write-Host "   • Redis Commander: http://localhost:8081" -ForegroundColor White

Write-Host "`n🔑 Database Credentials:" -ForegroundColor Cyan
Write-Host "   • MySQL: manager/managerpassword @ localhost:3307" -ForegroundColor White
Write-Host "   • Redis: redispassword @ localhost:6380" -ForegroundColor White

Write-Host "`n🚀 To start the application, run:" -ForegroundColor Green
Write-Host "   mvn spring-boot:run `"-Dspring-boot.run.arguments=--spring.profiles.active=dev`"" -ForegroundColor Yellow

Write-Host "`n📋 Quick Commands:" -ForegroundColor Cyan
Write-Host "   • Check containers: docker-compose ps" -ForegroundColor White
Write-Host "   • View logs: docker-compose logs [service-name]" -ForegroundColor White
Write-Host "   • Stop containers: docker-compose stop" -ForegroundColor White
Write-Host "   • Remove containers: docker-compose down" -ForegroundColor White

Write-Host "`n✨ Setup completed successfully!" -ForegroundColor Green
