#!/bin/bash

# Auto-deployment script for Dell Port Tracer
# This script downloads the latest files and restarts Docker container if changes are detected

# Configuration
WORK_DIR="/home/janzen"
CONTAINER_NAME="dell-port-tracer"
LOG_FILE="/home/janzen/auto-deploy.log"
GITHUB_RAW_URL="https://raw.githubusercontent.com/Crispy-Pasta/DellPortTracer/main"

# List of files to check and update
FILES_TO_CHECK=(
    "port_tracer_web.py"
    "requirements.txt" 
    "Dockerfile"
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
        log_message "ERROR: Failed to download $file from $url"
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

# Main deployment function
main() {
    log_message "Starting auto-deployment check..."
    
    # Change to work directory
    cd "$WORK_DIR"
    
    # Check each file for changes
    changes_detected=false
    files_checked=0
    files_changed=0
    
    for file in "${FILES_TO_CHECK[@]}"; do
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
        log_message "File changes detected. Proceeding with container update..."
        
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
                        log_message "Deployment successful - service is running on port 8443"
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
    else
        log_message "No changes detected. Container deployment not needed."
    fi
    
    log_message "Auto-deployment check completed"
}

# Run main function
main "$@"
