#!/bin/bash

# Auto-deployment script for Dell Port Tracer v2.1.3
# This script checks for repository changes and restarts Docker container if needed
# Updated for modular architecture and new container setup

# Configuration
REPO_DIR="/home/janzen/port-tracing-script"
CONTAINER_NAME="dell-port-tracer-v2.1.3"
LOG_FILE="/home/janzen/auto-deploy.log"
GITHUB_REPO="https://github.com/Crispy-Pasta/DellPortTracer.git"
DOCKER_IMAGE="dell-port-tracer"
ENV_FILE="/home/janzen/port-tracing-script/.env"

# Critical files to monitor for changes (updated for v2.1.3)
CRITICAL_FILES=(
    "port_tracer_web.py"
    "auth.py"
    "switch_manager.py"
    "utils.py"
    "api_routes.py"
    "vlan_management_v2.py"
    "requirements.txt" 
    "Dockerfile"
    "docker-compose.yml"
    "static/js/main.js"
    ".env"
)

# Function to log messages with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] v2.1.3 - $1" | tee -a "$LOG_FILE"
}

# Function to check if container is running
is_container_running() {
    docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Function to restart the container (updated for v2.1.3)
restart_container() {
    log_message "Stopping existing container..."
    docker stop "$CONTAINER_NAME" > /dev/null 2>&1
    docker rm "$CONTAINER_NAME" > /dev/null 2>&1
    
    log_message "Starting updated container with v2.1.3 configuration..."
    cd "$REPO_DIR"
    
    # Start container with proper network and env file
    docker run -d \
        --name "$CONTAINER_NAME" \
        --network port-tracing-script_default \
        --env-file "$ENV_FILE" \
        -p 5000:5000 \
        --restart unless-stopped \
        "$DOCKER_IMAGE":v2.1.3
    
    if [ $? -eq 0 ]; then
        log_message "Container restarted successfully"
        return 0
    else
        log_message "ERROR: Failed to restart container"
        return 1
    fi
}

# Function to rebuild Docker image (updated for v2.1.3)
rebuild_image() {
    log_message "Rebuilding Docker image with v2.1.3 features..."
    cd "$REPO_DIR"
    
    # Build with v2.1.3 tag
    docker build -t "$DOCKER_IMAGE":v2.1.3 .
    
    if [ $? -eq 0 ]; then
        log_message "Docker image rebuilt successfully with modular architecture"
        
        # Also tag as latest for compatibility
        docker tag "$DOCKER_IMAGE":v2.1.3 "$DOCKER_IMAGE":latest
        
        return 0
    else
        log_message "ERROR: Failed to rebuild Docker image"
        return 1
    fi
}

# Function to run database migration if needed
run_migration() {
    log_message "Running database migration for v2.1.3..."
    
    # Check if migration script exists
    if [ -f "$REPO_DIR/migrate_database.py" ]; then
        docker exec "$CONTAINER_NAME" python migrate_database.py > /dev/null 2>&1
        
        if [ $? -eq 0 ]; then
            log_message "Database migration completed successfully"
            return 0
        else
            log_message "WARNING: Database migration failed or not needed"
            return 0  # Don't fail deployment for migration issues
        fi
    else
        log_message "No migration script found, skipping migration"
        return 0
    fi
}

# Function to perform health check
health_check() {
    log_message "Performing health check..."
    
    # Wait for container to start
    sleep 10
    
    # Check if container is running
    if is_container_running; then
        # Check health endpoint
        local health_response=$(curl -s http://localhost:5000/health 2>/dev/null)
        
        if [ "$health_response" = '{"status":"healthy"}' ]; then
            log_message "Health check PASSED - Application is responding correctly"
            return 0
        else
            log_message "WARNING: Health check failed - Response: $health_response"
            return 1
        fi
    else
        log_message "ERROR: Container is not running after deployment"
        return 1
    fi
}

# Main deployment function (updated for v2.1.3)
main() {
    log_message "Starting auto-deployment check for v2.1.3..."
    
    # Check if repository directory exists
    if [ ! -d "$REPO_DIR" ]; then
        log_message "ERROR: Repository directory $REPO_DIR does not exist"
        exit 1
    fi
    
    # Change to repository directory
    cd "$REPO_DIR"
    
    # Fetch latest changes from remote
    git fetch origin main > /dev/null 2>&1
    
    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to fetch from remote repository"
        exit 1
    fi
    
    # Check if local is behind remote
    LOCAL_COMMIT=$(git rev-parse HEAD)
    REMOTE_COMMIT=$(git rev-parse origin/main)
    
    if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
        # No changes, but check if container is running
        if ! is_container_running; then
            log_message "No repo changes, but container not running. Starting container..."
            if restart_container; then
                health_check
            fi
        fi
        exit 0
    fi
    
    log_message "Changes detected in repository. Starting v2.1.3 deployment..."
    log_message "Local commit: $LOCAL_COMMIT"
    log_message "Remote commit: $REMOTE_COMMIT"
    
    # Pull the latest changes
    git pull origin main > /dev/null 2>&1
    
    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to pull changes from repository"
        exit 1
    fi
    
    log_message "Successfully pulled latest changes"
    
    # Check if container is currently running
    if is_container_running; then
        log_message "Container is currently running. Proceeding with v2.1.3 update..."
        
        # Rebuild Docker image with latest code
        if rebuild_image; then
            # Restart container with new image
            if restart_container; then
                # Run database migration
                run_migration
                
                # Perform health check
                if health_check; then
                    log_message "v2.1.3 deployment completed successfully"
                else
                    log_message "WARNING: Deployment completed but health check failed"
                fi
            else
                log_message "ERROR: v2.1.3 deployment failed during container restart"
                exit 1
            fi
        else
            log_message "ERROR: v2.1.3 deployment failed during image rebuild"
            exit 1
        fi
    else
        log_message "Container is not running. Building v2.1.3 image and starting container..."
        
        if rebuild_image; then
            if restart_container; then
                run_migration
                if health_check; then
                    log_message "Initial v2.1.3 deployment completed successfully"
                else
                    log_message "WARNING: Container started but health check failed"
                fi
            else
                log_message "ERROR: Failed to start v2.1.3 container"
                exit 1
            fi
        else
            log_message "ERROR: Failed to build v2.1.3 Docker image"
            exit 1
        fi
    fi
    
    log_message "Auto-deployment v2.1.3 completed successfully"
}

# Run main function
main "$@"
