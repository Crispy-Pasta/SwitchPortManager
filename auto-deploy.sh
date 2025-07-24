#!/bin/bash

# Auto-deployment script for Dell Port Tracer
# This script checks for repository changes and restarts Docker container if needed

# Configuration
REPO_DIR="/home/janzen/port-tracing-script"
CONTAINER_NAME="dell-port-tracer"
LOG_FILE="/home/janzen/auto-deploy.log"
GITHUB_REPO="https://github.com/Crispy-Pasta/DellPortTracer.git"

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
    cd "$REPO_DIR"
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
    
    # Check if repository directory exists
    if [ ! -d "$REPO_DIR" ]; then
        log_message "ERROR: Repository directory $REPO_DIR does not exist"
        exit 1
    fi
    
    # Change to repository directory
    cd "$REPO_DIR"
    
    # Fetch latest changes from remote
    git fetch origin main >/dev/null 2>&1
    
    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to fetch from remote repository"
        exit 1
    fi
    
    # Check if local is behind remote
    LOCAL_COMMIT=$(git rev-parse HEAD)
    REMOTE_COMMIT=$(git rev-parse origin/main)
    
    if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
        log_message "Repository is up to date. No deployment needed."
        exit 0
    fi
    
    log_message "Changes detected in repository. Starting deployment..."
    log_message "Local commit: $LOCAL_COMMIT"
    log_message "Remote commit: $REMOTE_COMMIT"
    
    # Pull the latest changes
    git pull origin main >/dev/null 2>&1
    
    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to pull changes from repository"
        exit 1
    fi
    
    log_message "Successfully pulled latest changes"
    
    # Check if container is currently running
    if is_container_running; then
        log_message "Container is currently running. Proceeding with update..."
        
        # Rebuild Docker image with latest code
        if rebuild_image; then
            # Restart container with new image
            if restart_container; then
                log_message "Deployment completed successfully"
                
                # Wait a few seconds and verify container is running
                sleep 5
                if is_container_running; then
                    log_message "Container health check: PASSED"
                else
                    log_message "WARNING: Container health check failed"
                fi
            else
                log_message "ERROR: Deployment failed during container restart"
                exit 1
            fi
        else
            log_message "ERROR: Deployment failed during image rebuild"
            exit 1
        fi
    else
        log_message "Container is not running. Building image and starting container..."
        
        if rebuild_image; then
            if restart_container; then
                log_message "Initial deployment completed successfully"
            else
                log_message "ERROR: Failed to start container"
                exit 1
            fi
        else
            log_message "ERROR: Failed to build Docker image"
            exit 1
        fi
    fi
    
    log_message "Auto-deployment completed successfully"
}

# Run main function
main "$@"
