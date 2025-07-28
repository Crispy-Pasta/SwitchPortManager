#!/bin/bash

# Production Deployment Script for Dell Switch Port Tracer v2.0
# This script handles proper synchronization of configuration files and deployment

set -e  # Exit on any error

# Configuration
REPO_DIR="/home/janzen/port-tracing-script"
CONTAINER_NAME="dell-port-tracer"
LOG_FILE="/home/janzen/production-deploy.log"
SWITCHES_FILE="/home/janzen/switches.json"
ENV_FILE="/home/janzen/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages with timestamp and color
log_message() {
    local level=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        "INFO")
            echo -e "${GREEN}[${timestamp}] INFO: ${message}${NC}" | tee -a "$LOG_FILE"
            ;;
        "WARN")
            echo -e "${YELLOW}[${timestamp}] WARN: ${message}${NC}" | tee -a "$LOG_FILE"
            ;;
        "ERROR")
            echo -e "${RED}[${timestamp}] ERROR: ${message}${NC}" | tee -a "$LOG_FILE"
            ;;
        "DEBUG")
            echo -e "${BLUE}[${timestamp}] DEBUG: ${message}${NC}" | tee -a "$LOG_FILE"
            ;;
    esac
}

# Function to check if container is running
is_container_running() {
    docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Function to validate configuration files
validate_configuration() {
    log_message "INFO" "Validating configuration files..."
    
    # Check switches.json
    if [ -f "$REPO_DIR/switches.json" ]; then
        if python3 -c "import json; json.load(open('$REPO_DIR/switches.json'))" 2>/dev/null; then
            log_message "INFO" "switches.json is valid JSON"
        else
            log_message "ERROR" "switches.json is invalid JSON"
            return 1
        fi
    else
        log_message "ERROR" "switches.json not found in repository"
        return 1
    fi
    
    # Check .env file exists on production server
    if [ ! -f "$ENV_FILE" ]; then
        log_message "WARN" ".env file not found at $ENV_FILE"
        log_message "INFO" "Please ensure .env file is configured on production server"
    fi
    
    return 0
}

# Function to sync configuration files
sync_configuration() {
    log_message "INFO" "Synchronizing configuration files..."
    
    # Sync switches.json
    if [ -f "$REPO_DIR/switches.json" ]; then
        if [ -f "$SWITCHES_FILE" ]; then
            if ! cmp -s "$REPO_DIR/switches.json" "$SWITCHES_FILE"; then
                log_message "INFO" "switches.json has changed, updating..."
                cp "$REPO_DIR/switches.json" "$SWITCHES_FILE"
                log_message "INFO" "switches.json synchronized successfully"
                return 0  # Return 0 to indicate changes were made
            else
                log_message "INFO" "switches.json is already up to date"
                return 1  # Return 1 to indicate no changes
            fi
        else
            log_message "INFO" "Creating switches.json in production location..."
            cp "$REPO_DIR/switches.json" "$SWITCHES_FILE"
            log_message "INFO" "switches.json created successfully"
            return 0
        fi
    else
        log_message "ERROR" "switches.json not found in repository"
        return 2  # Return 2 to indicate error
    fi
}

# Function to build Docker image
build_image() {
    log_message "INFO" "Building Docker image..."
    cd "$REPO_DIR"
    
    if docker build -t dell-port-tracer:latest . > /dev/null 2>&1; then
        log_message "INFO" "Docker image built successfully"
        return 0
    else
        log_message "ERROR" "Failed to build Docker image"
        return 1
    fi
}

# Function to deploy container
deploy_container() {
    local restart_needed=$1
    
    if is_container_running; then
        if [ "$restart_needed" = "true" ]; then
            log_message "INFO" "Restarting container with updates..."
            docker stop "$CONTAINER_NAME" > /dev/null 2>&1
            docker rm "$CONTAINER_NAME" > /dev/null 2>&1
        else
            log_message "INFO" "Container is running and no restart needed"
            return 0
        fi
    else
        log_message "INFO" "Container not running, starting fresh..."
    fi
    
    # Start container with proper configuration
    log_message "INFO" "Starting container with v2.0 configuration..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p 8443:5000 \
        -v /home/janzen/logs:/app/logs \
        -v "$SWITCHES_FILE:/app/switches.json" \
        --env-file "$ENV_FILE" \
        -e USE_WINDOWS_AUTH=true \
        -e CPU_SAFETY_ENABLED=true \
        -e CPU_GREEN_THRESHOLD=40.0 \
        -e CPU_YELLOW_THRESHOLD=60.0 \
        -e CPU_RED_THRESHOLD=80.0 \
        -e SWITCH_PROTECTION_ENABLED=true \
        -e MAX_CONNECTIONS_PER_SWITCH=8 \
        -e MAX_TOTAL_CONNECTIONS=64 \
        -e COMMANDS_PER_SECOND_LIMIT=10 \
        -e SYSLOG_ENABLED=false \
        --restart unless-stopped \
        --security-opt no-new-privileges \
        dell-port-tracer:latest
    
    if [ $? -eq 0 ]; then
        log_message "INFO" "Container started successfully"
        return 0
    else
        log_message "ERROR" "Failed to start container"
        return 1
    fi
}

# Function to perform health check
health_check() {
    log_message "INFO" "Performing health check..."
    sleep 10  # Wait for container to fully start
    
    local max_attempts=6
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8443/health > /dev/null 2>&1; then
            log_message "INFO" "Health check passed"
            
            # Get detailed health info
            local health_info=$(curl -s http://localhost:8443/health)
            log_message "INFO" "Health details: $health_info"
            return 0
        else
            log_message "WARN" "Health check failed (attempt $attempt/$max_attempts)"
            attempt=$((attempt + 1))
            sleep 10
        fi
    done
    
    log_message "ERROR" "Health check failed after $max_attempts attempts"
    return 1
}

# Function to display deployment summary
deployment_summary() {
    log_message "INFO" "=== DEPLOYMENT SUMMARY ==="
    
    if is_container_running; then
        log_message "INFO" "✅ Container Status: RUNNING"
    else
        log_message "ERROR" "❌ Container Status: NOT RUNNING"
    fi
    
    # Get container stats
    if is_container_running; then
        local container_info=$(docker inspect dell-port-tracer --format='{{.State.Status}} {{.State.StartedAt}}')
        log_message "INFO" "Container Info: $container_info"
        
        # Check switches count
        local switches_count=$(docker exec dell-port-tracer python3 -c "import json; data=json.load(open('/app/switches.json')); print(f'Sites: {len(data.get(\"sites\",{}))}, Total Switches: {sum(len(floor.get(\"switches\",{})) for site in data.get(\"sites\",{}).values() for floor in site.get(\"floors\",{}).values())}')" 2>/dev/null)
        log_message "INFO" "Switch Inventory: $switches_count"
    fi
    
    log_message "INFO" "=== END SUMMARY ==="
}

# Main deployment function
main() {
    log_message "INFO" "Starting Dell Switch Port Tracer v2.0 Production Deployment"
    log_message "INFO" "Repository: $REPO_DIR"
    log_message "INFO" "Container: $CONTAINER_NAME"
    
    # Validate configuration
    if ! validate_configuration; then
        log_message "ERROR" "Configuration validation failed"
        exit 1
    fi
    
    # Sync configuration files and check if changes were made
    sync_configuration
    local config_changed=$?
    
    # Build image
    if ! build_image; then
        log_message "ERROR" "Image build failed"
        exit 1
    fi
    
    # Deploy container (restart if config changed or if forced)
    local restart_needed="false"
    if [ "$config_changed" = "0" ] || [ "$1" = "--force" ]; then
        restart_needed="true"
    fi
    
    if ! deploy_container "$restart_needed"; then
        log_message "ERROR" "Container deployment failed"
        exit 1
    fi
    
    # Health check
    if ! health_check; then
        log_message "ERROR" "Health check failed"
        exit 1
    fi
    
    # Display summary
    deployment_summary
    
    log_message "INFO" "🎉 Production deployment completed successfully!"
    log_message "INFO" "🌐 Application URL: http://$(hostname -I | awk '{print $1}'):8443"
}

# Script entry point
case "${1:-}" in
    "--help"|"-h")
        echo "Dell Switch Port Tracer v2.0 Production Deployment Script"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --force    Force container restart even if no config changes"
        echo "  --help     Show this help message"
        echo ""
        echo "Features:"
        echo "  ✅ Automatic configuration synchronization"
        echo "  ✅ Docker image building and deployment"
        echo "  ✅ Health checks and validation"
        echo "  ✅ v2.0 feature configuration"
        echo "  ✅ Comprehensive logging"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
