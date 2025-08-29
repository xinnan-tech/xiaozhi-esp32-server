#!/bin/bash

# XiaoZhi Content Library Migration Script
# This script provides an easy way to run the content library migration
# with proper environment setup and error handling.

set -e  # Exit on any error

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
JAR_NAME="manager-api.jar"
MAIN_CLASS="xiaozhi.migration.MigrationRunner"
LOG_FILE="logs/content-migration.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
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

# Function to print usage
print_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

XiaoZhi Content Library Migration Script

OPTIONS:
    -h, --help              Show this help message
    -p, --path PATH         Specify xiaozhi-server directory path (default: auto-detect)
    -b, --batch-size SIZE   Batch size for database operations (default: 100)
    -d, --dry-run          Perform a dry run without actual database changes
    -v, --verbose          Enable verbose logging
    -c, --check-only       Only check prerequisites without running migration
    
EXAMPLES:
    $0                                    # Run with default settings
    $0 --path /path/to/xiaozhi-server    # Specify custom path
    $0 --batch-size 50 --verbose         # Custom batch size with verbose logging
    $0 --check-only                      # Check prerequisites only
    $0 --dry-run                         # Test run without database changes

ENVIRONMENT VARIABLES:
    XIAOZHI_SERVER_PATH     Override xiaozhi-server directory path
    MIGRATION_BATCH_SIZE    Override batch size for migration
    JAVA_OPTS               Additional JVM options
EOF
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check if Java is available
    if ! command -v java &> /dev/null; then
        print_error "Java is not installed or not in PATH"
        return 1
    fi
    
    local java_version=$(java -version 2>&1 | head -n 1 | cut -d'"' -f2)
    print_info "Java version: $java_version"
    
    # Check if Maven is available (for building if needed)
    if ! command -v mvn &> /dev/null; then
        print_warning "Maven is not available - assuming JAR is pre-built"
    fi
    
    # Check if JAR file exists or can be built
    if [[ -f "target/$JAR_NAME" ]]; then
        print_info "Found JAR file: target/$JAR_NAME"
    elif [[ -f "$JAR_NAME" ]]; then
        print_info "Found JAR file: $JAR_NAME"
    else
        print_info "JAR file not found - attempting to build..."
        if command -v mvn &> /dev/null; then
            mvn clean package -DskipTests
            if [[ $? -ne 0 ]]; then
                print_error "Failed to build JAR file"
                return 1
            fi
        else
            print_error "JAR file not found and Maven not available for building"
            return 1
        fi
    fi
    
    return 0
}

# Function to find xiaozhi-server path
find_xiaozhi_server_path() {
    local custom_path="$1"
    
    # Use custom path if provided
    if [[ -n "$custom_path" ]]; then
        if [[ -d "$custom_path" ]]; then
            echo "$custom_path"
            return 0
        else
            print_error "Specified path does not exist: $custom_path"
            return 1
        fi
    fi
    
    # Check environment variable
    if [[ -n "$XIAOZHI_SERVER_PATH" ]]; then
        if [[ -d "$XIAOZHI_SERVER_PATH" ]]; then
            echo "$XIAOZHI_SERVER_PATH"
            return 0
        else
            print_warning "Environment XIAOZHI_SERVER_PATH is set but directory does not exist: $XIAOZHI_SERVER_PATH"
        fi
    fi
    
    # Auto-detect possible paths
    local possible_paths=(
        "./xiaozhi-server"
        "../xiaozhi-server"
        "../../xiaozhi-server"
        "/opt/xiaozhi/xiaozhi-server"
        "/home/$(whoami)/xiaozhi-server"
    )
    
    for path in "${possible_paths[@]}"; do
        if [[ -d "$path" ]]; then
            echo "$(realpath "$path")"
            return 0
        fi
    done
    
    print_error "Could not find xiaozhi-server directory"
    print_info "Please specify the path using --path option or set XIAOZHI_SERVER_PATH environment variable"
    return 1
}

# Function to validate xiaozhi-server structure
validate_xiaozhi_structure() {
    local path="$1"
    
    print_info "Validating xiaozhi-server structure at: $path"
    
    # Check music directory
    if [[ ! -d "$path/music" ]]; then
        print_error "Music directory not found: $path/music"
        return 1
    fi
    
    # Check stories directory
    if [[ ! -d "$path/stories" ]]; then
        print_error "Stories directory not found: $path/stories"
        return 1
    fi
    
    # Check for metadata files
    local music_count=0
    local story_count=0
    
    for lang_dir in "$path/music"/*; do
        if [[ -d "$lang_dir" && -f "$lang_dir/metadata.json" ]]; then
            ((music_count++))
            print_info "Found music metadata: $(basename "$lang_dir")"
        fi
    done
    
    for genre_dir in "$path/stories"/*; do
        if [[ -d "$genre_dir" && -f "$genre_dir/metadata.json" ]]; then
            ((story_count++))
            print_info "Found story metadata: $(basename "$genre_dir")"
        fi
    done
    
    if [[ $music_count -eq 0 && $story_count -eq 0 ]]; then
        print_error "No metadata files found in music or stories directories"
        return 1
    fi
    
    print_success "Found $music_count music categories and $story_count story genres"
    return 0
}

# Function to run migration
run_migration() {
    local xiaozhi_path="$1"
    local batch_size="${2:-100}"
    local dry_run="${3:-false}"
    local verbose="${4:-false}"
    
    print_info "Starting Content Library Migration..."
    print_info "XiaoZhi Server Path: $xiaozhi_path"
    print_info "Batch Size: $batch_size"
    
    # Prepare JVM options
    local jvm_opts="-Xmx2g -Dspring.profiles.active=migration"
    
    if [[ "$verbose" == "true" ]]; then
        jvm_opts="$jvm_opts -Dlogging.level.xiaozhi.migration=DEBUG"
    fi
    
    # Add custom JAVA_OPTS if set
    if [[ -n "$JAVA_OPTS" ]]; then
        jvm_opts="$jvm_opts $JAVA_OPTS"
    fi
    
    # Set environment variables
    export MIGRATION_BASE_PATH="$xiaozhi_path"
    export MIGRATION_BATCH_SIZE="$batch_size"
    
    if [[ "$dry_run" == "true" ]]; then
        export MIGRATION_DRY_RUN="true"
        print_warning "Running in DRY RUN mode - no database changes will be made"
    fi
    
    # Create logs directory
    mkdir -p logs
    
    # Find JAR file
    local jar_file=""
    if [[ -f "target/$JAR_NAME" ]]; then
        jar_file="target/$JAR_NAME"
    elif [[ -f "$JAR_NAME" ]]; then
        jar_file="$JAR_NAME"
    else
        print_error "JAR file not found"
        return 1
    fi
    
    # Run migration
    print_info "Executing migration..."
    
    if java $jvm_opts -jar "$jar_file" 2>&1 | tee "$LOG_FILE"; then
        print_success "Migration completed successfully!"
        print_info "Migration log saved to: $LOG_FILE"
        
        # Show summary from log
        if [[ -f "$LOG_FILE" ]]; then
            print_info "Migration Summary:"
            grep -A 20 "MIGRATION SUMMARY" "$LOG_FILE" | tail -20 || true
        fi
        
        return 0
    else
        print_error "Migration failed! Check log file: $LOG_FILE"
        return 1
    fi
}

# Main script
main() {
    local xiaozhi_path=""
    local batch_size="100"
    local dry_run="false"
    local verbose="false"
    local check_only="false"
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                print_usage
                exit 0
                ;;
            -p|--path)
                xiaozhi_path="$2"
                shift 2
                ;;
            -b|--batch-size)
                batch_size="$2"
                shift 2
                ;;
            -d|--dry-run)
                dry_run="true"
                shift
                ;;
            -v|--verbose)
                verbose="true"
                shift
                ;;
            -c|--check-only)
                check_only="true"
                shift
                ;;
            *)
                print_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
    
    print_info "XiaoZhi Content Library Migration"
    print_info "=================================="
    
    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi
    
    # Find xiaozhi-server path
    if ! xiaozhi_path=$(find_xiaozhi_server_path "$xiaozhi_path"); then
        exit 1
    fi
    
    # Validate structure
    if ! validate_xiaozhi_structure "$xiaozhi_path"; then
        exit 1
    fi
    
    # Exit if check-only mode
    if [[ "$check_only" == "true" ]]; then
        print_success "Prerequisites check completed successfully!"
        exit 0
    fi
    
    # Run migration
    if run_migration "$xiaozhi_path" "$batch_size" "$dry_run" "$verbose"; then
        print_success "Migration script completed successfully!"
        exit 0
    else
        print_error "Migration script failed!"
        exit 1
    fi
}

# Run main function
main "$@"