#!/bin/bash

# Auto-deployment script for Dell Port Tracer
# This script pulls changes from GitHub and restarts Docker container when updates are detected

# Configuration
WORK_DIR="/home/janzen"
CONTAINER_NAME="dell-port-tracer"
LOG_FILE="/home/janzen/auto-deploy.log"
GITHUB_RAW_URL="https://raw.githubusercontent.com/Crispy-Pasta/DellPortTracer/main"

# List of critical files to monitor for changes
CRITICAL_FILES=(
    "port_tracer_web.py"
    "requirements.txt" 
    "Dockerfile"
    "nt_auth_integration.py"
)

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

# Function to download file and check if it changed
download_and_check() {
    local file="$1"
    local url="${GITHUB_RAW_URL}/${file}"
    local temp_file="${WORK_DIR}/${file}.tmp"
    local current_file="${WORK_DIR}/${file}"
    
    # Download the file
    curl -s -f -o "$temp_file" "$url"
    
    if [ $? -ne 0 ]; then
        log_message "WARNING: Failed to download $file from GitHub"
        rm -f "$temp_file"
        return 1
    fi
    
    # Check if file exists and compare
    if [ -f "$current_file" ]; then
        if cmp -s "$temp_file" "$current_file"; then
            # Files are identical
            rm -f "$temp_file"
            return 0
        else
            # Files are different
            log_message "Changes detected in $file"
            mv "$temp_file" "$current_file"
            return 2
        fi
    else
        # File doesn't exist, move the new one
        log_message "New file detected: $file"
        mv "$temp_file" "$current_file"
        return 2
    fi
}

# Function to get latest commit hash from GitHub API
get_remote_commit() {
    curl -s "https://api.github.com/repos/Crispy-Pasta/DellPortTracer/commits/main" 2>/dev/null | grep '"sha"' | head -1 | cut -d'"' -f4 | cut -c1-7
}

# Main deployment function
main() {
    log_message "Starting auto-deployment check..."
    
    # Change to work directory
    cd "$WORK_DIR"
    
    # Get current commit hash if we have one stored
    LAST_COMMIT_FILE="${WORK_DIR}/.last_commit"
    if [ -f "$LAST_COMMIT_FILE" ]; then
        LAST_COMMIT=$(cat "$LAST_COMMIT_FILE")
    else
        LAST_COMMIT=""
    fi
    
    # Get latest commit from GitHub
    LATEST_COMMIT=$(get_remote_commit)
    
    if [ -z "$LATEST_COMMIT" ]; then
        log_message "WARNING: Failed to get latest commit from GitHub, falling back to health check"
        # Fallback to health check only
        perform_health_check
        return
    fi
    
    # Check if we need to update
    if [ "$LAST_COMMIT" = "$LATEST_COMMIT" ]; then
        log_message "Repository is up to date (commit: $LATEST_COMMIT)"
        # Still perform health check
        perform_health_check
        return 0
    fi
    
    log_message "New changes detected in repository!"
    log_message "Current commit: $LAST_COMMIT"
    log_message "Latest commit: $LATEST_COMMIT"
    
    # Check each critical file for changes
    changes_detected=false
    files_checked=0
    files_changed=0
    
    for file in "${CRITICAL_FILES[@]}"; do
        files_checked=$((files_checked + 1))
        download_and_check "$file"
        result=$?
        
        if [ $result -eq 2 ]; then
            changes_detected=true
            files_changed=$((files_changed + 1))
        elif [ $result -eq 1 ]; then
            log_message "WARNING: Failed to check $file"
        fi
    done
    
    log_message "Checked $files_checked files, $files_changed files changed"
    
    if [ "$changes_detected" = true ]; then
        log_message "Critical file changes detected. Proceeding with deployment..."
        
        # Rebuild Docker image with latest code
        if rebuild_image; then
            # Restart container with new image
            if restart_container; then
                log_message "Deployment completed successfully"
                
                # Wait and verify container is running
                sleep 5
                if is_container_running; then
                    # Test service health
                    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8443/ || echo "000")
                    
                    if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ]; then
                        log_message "Post-deployment health check: PASSED (HTTP $HTTP_STATUS)"
                        log_message "🚀 Deployment successful - service updated and running on port 8443"
                        # Update the last commit file
                        echo "$LATEST_COMMIT" > "$LAST_COMMIT_FILE"
                    else
                        log_message "WARNING: Post-deployment health check failed (HTTP $HTTP_STATUS)"
                    fi
                else
                    log_message "ERROR: Container health check failed after deployment"
                fi
            else
                log_message "ERROR: Deployment failed during container restart"
                return 1
            fi
        else
            log_message "ERROR: Deployment failed during image rebuild"
            return 1
        fi
    else
        log_message "No critical file changes detected, updating commit reference only"
        echo "$LATEST_COMMIT" > "$LAST_COMMIT_FILE"
        # Still perform health check
        perform_health_check
    fi
    
    log_message "Auto-deployment check completed"
}

# Function to perform health check
perform_health_check() {
    if is_container_running; then
        # Test if the service responds
        HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8443/ || echo "000")
        
        if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ]; then
            log_message "Service health check: PASSED (HTTP $HTTP_STATUS)"
        else
            log_message "Service health check: FAILED (HTTP $HTTP_STATUS)"
            log_message "Attempting to restart unhealthy container..."
            
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
}

# Run main function
main "$@"
