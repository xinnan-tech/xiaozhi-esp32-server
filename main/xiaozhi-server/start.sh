#!/bin/bash

# Xiaozhi Server Startup Script
# Usage: ./start.sh --region <region> --action <action>
# Region: sg, us, local
# Action: server, all

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Display banner
echo -e "${CYAN}"
echo "=================================="
echo "  Xiaozhi Server Startup Script"
echo "=================================="
echo -e "${NC}"

# Function to display usage
show_usage() {
    echo -e "${RED}Error: Missing or invalid arguments${NC}"
    echo ""
    echo "Usage: $0 --region <region> --action <action>"
    echo ""
    echo "Options:"
    echo "  -r, --region <region>   Deployment region"
    echo "                          Values: sg, us, local"
    echo ""
    echo "  -a, --action <action>   Action to perform"
    echo "                          Values: server, web, all"
    echo ""
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Region details:"
    echo "  sg     - Singapore (REGION=SINGAPORE)"
    echo "  us     - US West 2 (REGION=US-WEST-2)"
    echo "  local  - Local development (REGION=LOCAL)"
    echo ""
    echo "Action details:"
    echo "  server - Rebuild and restart xiaozhi-esp32-server"
    echo "  web    - Rebuild and restart xiaozhi-esp32-server-web (manager-api + manager-web)"
    echo "  all    - Rebuild and restart server + web (does not rebuild db/redis)"
    echo ""
    echo "Examples:"
    echo "  $0 --region sg --action server"
    echo "  $0 -r local -a web"
    echo "  $0 --region local --action all"
    exit 1
}

# Parse command line arguments
REGION=""
ACTION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -r|--region)
            REGION="$2"
            shift 2
            ;;
        -a|--action)
            ACTION="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo -e "${RED}Error: Unknown option '$1'${NC}"
            echo ""
            show_usage
            ;;
    esac
done

# Check if required arguments are provided
if [ -z "$REGION" ] || [ -z "$ACTION" ]; then
    show_usage
fi

# Validate region
case $REGION in
    sg|SG)
        COMPOSE_FILE="docker-compose_sg_all.yml"
        REGION_NAME="Singapore"
        REGION_ENV="SINGAPORE"
        ;;
    us|US)
        COMPOSE_FILE="docker-compose_us_all.yml"
        REGION_NAME="US West 2"
        REGION_ENV="US-WEST-2"
        ;;
    local|LOCAL)
        COMPOSE_FILE="docker-compose_local_all.yml"
        REGION_NAME="Local"
        REGION_ENV="LOCAL"
        ;;
    *)
        echo -e "${RED}Error: Invalid region '${REGION}'${NC}"
        echo "Valid regions: sg, us, local"
        exit 1
        ;;
esac

# Validate action
case $ACTION in
    server|SERVER)
        ACTION_NAME="Server Only"
        SERVICES="xiaozhi-esp32-server"
        ;;
    web|WEB)
        ACTION_NAME="Web Only (Manager API + Web)"
        SERVICES="xiaozhi-esp32-server-web"
        ;;
    all|ALL)
        ACTION_NAME="Server + Web"
        SERVICES="xiaozhi-esp32-server xiaozhi-esp32-server-web"
        ;;
    *)
        echo -e "${RED}Error: Invalid action '${ACTION}'${NC}"
        echo "Valid actions: server, web, all"
        exit 1
        ;;
esac

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}Error: Compose file '${COMPOSE_FILE}' not found${NC}"
    exit 1
fi

# ============================================================================
# Auto-detect public IP and update .env file
# ============================================================================
get_public_ip() {
    local ip=""
    
    # Method 1: AWS EC2 Metadata Service (IMDSv1)
    ip=$(curl -s --connect-timeout 2 http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)
    
    # Method 2: AWS EC2 Metadata Service (IMDSv2)
    if [ -z "$ip" ]; then
        local token=$(curl -s --connect-timeout 2 -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600" 2>/dev/null || true)
        if [ -n "$token" ]; then
            ip=$(curl -s --connect-timeout 2 -H "X-aws-ec2-metadata-token: $token" http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true)
        fi
    fi
    
    # Method 3: External service
    if [ -z "$ip" ]; then
        ip=$(curl -s --connect-timeout 3 https://ifconfig.me 2>/dev/null || true)
    fi
    
    # Method 4: Backup external service
    if [ -z "$ip" ]; then
        ip=$(curl -s --connect-timeout 3 https://api.ipify.org 2>/dev/null || true)
    fi
    
    echo "$ip"
}

init_env_file() {
    local ENV_FILE=".env"
    local public_ip=""
    
    echo -e "${BLUE}→ Detecting public IP...${NC}"
    public_ip=$(get_public_ip)
    
    if [ -z "$public_ip" ]; then
        echo -e "${YELLOW}  Warning: Cannot detect public IP, using localhost${NC}"
        public_ip="localhost"
    else
        echo -e "${GREEN}  Public IP: ${public_ip}${NC}"
    fi
    
    # Build URLs
    local websocket_url="ws://${public_ip}:8000/xiaozhi/v1/"
    local ota_url="http://${public_ip}:8003/xiaozhi/ota/"
    
    # Create or update .env file
    if [ -f "$ENV_FILE" ]; then
        # Remove old entries (keep other configs)
        grep -v "^PUBLIC_IP=" "$ENV_FILE" | grep -v "^WEBSOCKET_URL=" | grep -v "^OTA_URL=" | grep -v "^# Auto-generated" > "${ENV_FILE}.tmp" 2>/dev/null || true
        mv "${ENV_FILE}.tmp" "$ENV_FILE" 2>/dev/null || touch "$ENV_FILE"
    else
        touch "$ENV_FILE"
    fi
    
    # Append new config
    echo "" >> "$ENV_FILE"
    echo "# Auto-generated by start.sh at $(date '+%Y-%m-%d %H:%M:%S')" >> "$ENV_FILE"
    echo "PUBLIC_IP=$public_ip" >> "$ENV_FILE"
    echo "WEBSOCKET_URL=$websocket_url" >> "$ENV_FILE"
    echo "OTA_URL=$ota_url" >> "$ENV_FILE"
    
    echo -e "${GREEN}  WEBSOCKET_URL=${websocket_url}${NC}"
    echo ""
}

# Initialize environment variables
init_env_file

echo -e "${GREEN}Configuration:${NC}"
echo "  Region: ${REGION_NAME} (${REGION_ENV})"
echo "  Action: ${ACTION_NAME}"
echo "  Compose file: ${COMPOSE_FILE}"
echo ""

# Display current status
echo -e "${BLUE}Current container status:${NC}"
docker ps --filter name=xiaozhi --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "No containers running"
echo ""

# Execute action with rebuild
echo -e "${YELLOW}→ Rebuilding and starting: ${ACTION_NAME}${NC}"
echo -e "${CYAN}   Services: ${SERVICES}${NC}"
echo ""

# Use up --build -d to rebuild images and start containers
docker compose -f "$COMPOSE_FILE" up --build -d $SERVICES

echo ""
echo -e "${GREEN}✓ Operation completed${NC}"
echo ""

# Display final status
echo -e "${BLUE}Updated container status:${NC}"
docker ps --filter name=xiaozhi --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Show logs option
echo -e "${CYAN}To view logs, run:${NC}"
if [ -n "$SERVICES" ]; then
    echo "  docker compose -f $COMPOSE_FILE logs -f $SERVICES"
else
    echo "  docker compose -f $COMPOSE_FILE logs -f"
fi
echo ""

