#!/bin/bash

# XiaoZhi Content Library Migration Validation Script
# This script validates that the migration was successful

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info "XiaoZhi Content Library Migration Validation"
print_info "============================================"

# Find JAR file
JAR_FILE=""
if [[ -f "target/manager-api.jar" ]]; then
    JAR_FILE="target/manager-api.jar"
elif [[ -f "manager-api.jar" ]]; then
    JAR_FILE="manager-api.jar"
else
    print_error "JAR file not found. Please build the project first."
    exit 1
fi

print_info "Using JAR file: $JAR_FILE"

# Run validation
print_info "Starting migration validation..."

if java -Xmx1g -Dspring.profiles.active=validation -jar "$JAR_FILE"; then
    print_success "Migration validation completed successfully!"
else
    print_error "Migration validation failed!"
    exit 1
fi