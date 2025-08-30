#!/bin/bash

echo "================================================"
echo "Rebuilding and Restarting Manager-API"
echo "================================================"

# Navigate to manager-api directory
cd main/manager-api

# Check if Maven is installed
if ! command -v mvn &> /dev/null; then
    echo "Maven is not installed. Please install Maven first."
    exit 1
fi

# Clean and build the project
echo "Building manager-api with Maven..."
mvn clean package -DskipTests

if [ $? -ne 0 ]; then
    echo "Build failed!"
    exit 1
fi

echo "Build successful!"

# Check if PM2 is available
if command -v pm2 &> /dev/null; then
    echo "Restarting manager-api with PM2..."
    pm2 restart manager-api
    
    # Show the status
    pm2 status manager-api
    
    # Show recent logs
    echo ""
    echo "Recent logs:"
    pm2 logs manager-api --lines 20 --nostream
else
    echo "PM2 not found. You'll need to restart manager-api manually."
    echo ""
    echo "If running with Java directly, use:"
    echo "  java -jar target/manager-api-*.jar"
fi

echo ""
echo "================================================"
echo "Manager-API rebuild complete!"
echo "SYSTEM_PLUGIN_STORY is now included in default plugins"
echo "================================================"