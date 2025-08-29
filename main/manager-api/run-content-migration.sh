#!/bin/bash

# Content Library Migration Runner Script
# This script runs the ContentLibraryMigration to populate the database with music and stories

echo "=========================================="
echo "Content Library Migration Script"
echo "=========================================="
echo ""

# Navigate to the project directory
cd /Users/craftech360/Downloads/app/cheeko_server/main/manager-api

# Check if the project has been built
if [ ! -f "target/manager-api.jar" ]; then
    echo "Building the project first..."
    mvn clean package -DskipTests
    if [ $? -ne 0 ]; then
        echo "Build failed. Please check your Maven configuration."
        exit 1
    fi
fi

echo "Starting content library migration..."
echo ""

# Run the migration with the migration profile
java -jar target/manager-api.jar \
    --spring.profiles.active=migration,dev \
    --spring.main.web-application-type=none \
    --spring.main.banner-mode=off

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Migration completed successfully!"
    echo "=========================================="
else
    echo ""
    echo "=========================================="
    echo "Migration failed. Check the logs above."
    echo "=========================================="
    exit 1
fi