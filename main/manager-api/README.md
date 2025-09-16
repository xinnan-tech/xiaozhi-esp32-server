This is a development document. If you need to deploy the Xiaozhi server, [click here to view the deployment tutorial](../../README.md#deployment-documentation)

# XiaoZhi ESP32 Manager API

This project is developed based on the SpringBoot framework and serves as the backend API for the XiaoZhi ESP32 management system.

## Development Environment Requirements

- **JDK 21+**
- **Maven 3.8+**
- **Docker & Docker Compose** (for local database and cache)
- **MySQL 8.0+** (via Docker)
- **Redis 7.0+** (via Docker)

## Quick Start (Development Mode)

### Option 1: Automated Setup (Recommended)

```powershell
# Run the automated setup script
.\dev-setup.ps1

# Then start the application
mvn spring-boot:run "-Dspring-boot.run.arguments=--spring.profiles.active=dev"
```

### Option 2: Manual Setup

#### Step 1: Start Docker Containers

First, start the required MySQL and Redis containers:

```bash
# Navigate to the manager-api directory
cd D:\cheekofinal\xiaozhi-esp32-server\main\manager-api

# Start Docker containers (MySQL, Redis, phpMyAdmin, Redis Commander)
docker-compose up -d

# Verify containers are running
docker-compose ps
```

#### Step 2: Run the Spring Boot Application

```bash
# Clean and compile the project
mvn clean compile

# Run the application with dev profile
mvn spring-boot:run "-Dspring-boot.run.arguments=--spring.profiles.active=dev"
```

## Docker Services

The `docker-compose.yml` includes the following services:

| Service | Port | Description | Credentials |
|---------|------|-------------|--------------|
| **manager-api-db** (MySQL) | 3307 | MySQL database | User: `manager`<br>Password: `managerpassword`<br>Database: `manager_api` |
| **manager-api-redis** | 6380 | Redis cache | Password: `redispassword` |
| **phpMyAdmin** | 8080 | MySQL web interface | User: `root`<br>Password: `rootpassword` |
| **redis-commander** | 8081 | Redis web interface | Auto-configured |

## Access Points

- **API Documentation**: http://localhost:8002/xiaozhi/doc.html
- **Application Base URL**: http://localhost:8002/toy
- **phpMyAdmin**: http://localhost:8080
- **Redis Commander**: http://localhost:8081

## Configuration

The development configuration is located in:
```
src/main/resources/application-dev.yml
```

This configuration is set up to use the local Docker containers:
- MySQL on localhost:3307
- Redis on localhost:6380

## Database Management

### Manual Database Connection
```bash
# Connect to MySQL container
docker exec -it manager-api-db mysql -u manager -p'managerpassword' manager_api

# Connect to Redis container
docker exec -it manager-api-redis redis-cli -a redispassword
```

### Database Migration
The application uses Liquibase for database migrations. Migrations run automatically on startup.

## Troubleshooting

### Container Issues
```bash
# Check container logs
docker-compose logs manager-api-db
docker-compose logs manager-api-redis

# Restart containers
docker-compose restart

# Stop and remove all containers
docker-compose down

# Stop and remove containers with volumes
docker-compose down -v
```

### Application Issues
```bash
# Check if ports are available
netstat -an | findstr :8002
netstat -an | findstr :3307
netstat -an | findstr :6380

# Clean Maven build
mvn clean install
```

### Common Error Solutions

1. **Port Conflicts**: If ports 3307, 6380, 8080, or 8081 are in use, modify the ports in `docker-compose.yml`

2. **Database Connection Failed**: 
   - Ensure Docker containers are running
   - Wait for MySQL health check to pass (can take 30-60 seconds)
   - Check if credentials match in `application-dev.yml`

3. **Redis Connection Failed**:
   - Verify Redis container is healthy
   - Check Redis password configuration

## Development Workflow

1. **First Time Setup**:
   ```bash
   docker-compose up -d
   mvn clean compile
   mvn spring-boot:run "-Dspring-boot.run.arguments=--spring.profiles.active=dev"
   ```

2. **Daily Development**:
   ```bash
   # Start containers (if not running)
   docker-compose start
   
   # Run application
   mvn spring-boot:run "-Dspring-boot.run.arguments=--spring.profiles.active=dev"
   ```

3. **Cleanup**:
   ```bash
   # Stop application (Ctrl+C)
   # Stop containers
   docker-compose stop
   ```

## Project Structure

When developing, use a code editor and select the `manager-api` folder as the project directory when importing the project.

```
manager-api/
├── docker-compose.yml          # Docker services configuration
├── src/main/resources/
│   ├── application.yml         # Base configuration
│   ├── application-dev.yml     # Development configuration
│   └── application-prod.yml    # Production configuration
├── docker/
│   ├── mysql/init/            # MySQL initialization scripts
│   └── redis/                 # Redis configuration
└── target/                    # Compiled classes
```
