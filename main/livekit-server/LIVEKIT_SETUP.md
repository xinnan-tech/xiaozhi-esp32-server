# LiveKit Server Local Setup

This setup uses the existing Redis instance from manager-api running on port 6380.

## Prerequisites

1. **Docker Desktop** must be installed and running
2. **Manager-API Redis** must be running on port 6380 with password `redispassword`
   - Start it with: `cd ../manager-api && docker-compose -f "docker-compose (1).yml" up -d manager-api-redis`

## Quick Start

### Option 1: Start only LiveKit Server
```bash
# Windows
start-livekit.bat

# Or manually
docker-compose up -d livekit
```

### Option 2: Start LiveKit Server + Python Agent
```bash
# Windows
start-all.bat

# Or manually
docker-compose up --build
```

## Configuration

### LiveKit Server
- **WebRTC Signaling**: ws://localhost:7880
- **HTTP API**: http://localhost:7882
- **TURN/STUN**: localhost:7881
- **API Key**: devkey
- **API Secret**: secret

### Redis Connection
- **Host**: localhost (or host.docker.internal from Docker)
- **Port**: 6380
- **Password**: redispassword

## Files Created

1. **docker-compose.yml** - Defines LiveKit server and agent services
2. **livekit.yaml** - LiveKit server configuration
3. **.env** - Environment variables for local development
4. **start-livekit.bat** - Start only LiveKit server
5. **start-all.bat** - Start LiveKit server and agent

## Testing the Connection

### 1. Check if LiveKit is running:
```bash
curl http://localhost:7882/healthz
```

### 2. View LiveKit logs:
```bash
docker-compose logs -f livekit
```

### 3. Test with LiveKit CLI:
```bash
# Install LiveKit CLI
go install github.com/livekit/livekit-cli@latest

# Create a test room
livekit-cli create-room --api-key devkey --api-secret secret --url ws://localhost:7880 test-room
```

## Switching Between Local and Cloud

To switch back to cloud LiveKit:
1. Edit `.env` file
2. Comment out local configuration
3. Uncomment cloud configuration

## Troubleshooting

### Redis Connection Issues
- Ensure manager-api Redis is running: `docker ps | grep redis`
- Check Redis logs: `docker logs manager-api-redis`

### LiveKit Server Issues
- Check logs: `docker-compose logs livekit`
- Ensure ports 7880-7882 are not in use
- Verify network exists: `docker network ls`

### Network Issues
If the network doesn't exist:
```bash
docker network create manager-api_manager-api-network
```

## Stop Services

```bash
# Stop LiveKit and agent
docker-compose down

# Stop only LiveKit, keep agent running
docker-compose stop livekit
```