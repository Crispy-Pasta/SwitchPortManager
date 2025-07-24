#!/bin/bash

# Auto-deployment script for Dell Port Tracer
# This script works with both public and private repositories

# Configuration
WORK_DIR="/home/janzen"
CONTAINER_NAME="dell-port-tracer"
LOG_FILE="/home/janzen/auto-deploy.log"

# Function to log messages with timestamp  
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check if container is running
is_container_running() {
    docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Function to restart the container
restart_container() {
    log_message "Stopping existing container..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1
    
    log_message "Starting updated container..."
    docker run -d \
        --name "$CONTAINER_NAME" \
        -p 8443:5000 \
        -v /home/janzen/logs:/app/logs \
        -v /home/janzen/switches.json:/app/switches.json \
        --env-file /home/janzen/.env \
        --restart unless-stopped \
        dell-port-tracer:latest
    
    if [ $? -eq 0 ]; then
        log_message "Container restarted successfully"
        return 0
    else
        log_message "ERROR: Failed to restart container"
        return 1
    fi
}

# Function to rebuild Docker image
rebuild_image() {
    log_message "Rebuilding Docker image..."
    cd "$WORK_DIR"
    docker build -t dell-port-tracer:latest . >/dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        log_message "Docker image rebuilt successfully"
        return 0
    else
        log_message "ERROR: Failed to rebuild Docker image"
        return 1
    fi
}

# Main deployment function
main() {
    log_message "Starting auto-deployment check..."
    
    # Change to work directory
    cd "$WORK_DIR"
    
    # For now, since repository access is limited, we'll just check if container is running
    # and restart it periodically to ensure it's healthy
    
    if is_container_running; then
        log_message "Container is running. Checking health..."
        
        # Test if the service responds
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8443/ || echo "000")
        
        if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ]; then
            log_message "Service health check: PASSED (HTTP $HTTP_STATUS)"
            log_message "No deployment needed - service is healthy"
        else
            log_message "Service health check: FAILED (HTTP $HTTP_STATUS)"
            log_message "Attempting to restart container..."
            
            if restart_container; then
                sleep 5
                if is_container_running; then
                    log_message "Container restart successful"
                else
                    log_message "WARNING: Container failed to start after restart"
                fi
            fi
        fi
    else
        log_message "Container is not running. Starting container..."
        
        if restart_container; then
            sleep 5
            if is_container_running; then
                log_message "Container started successfully"
            else
                log_message "ERROR: Failed to start container"
            fi
        fi
    fi
    
    log_message "Auto-deployment check completed"
}

# Run main function
main "$@"
