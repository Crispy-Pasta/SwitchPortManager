#!/bin/bash

# Simplified Auto-deployment script for Dell Port Tracer
# This script downloads the latest files and restarts Docker container if needed

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
    "switches.json"
    "README.md"
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
    curl -s -o "$temp_file" "$url"
    
    if [ $? -ne 0 ]; then
        log_message "ERROR: Failed to download $file"
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
    curl -s "https://api.github.com/repos/Crispy-Pasta/DellPortTracer/commits/main" | grep '"sha"' | head -1 | cut -d'"' -f4 | cut -c1-7
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
        log_message "ERROR: Failed to get latest commit from GitHub"
        exit 1
    fi
    
    if [ "$LAST_COMMIT" = "$LATEST_COMMIT" ]; then
        log_message "Repository is up to date (commit: $LATEST_COMMIT). No deployment needed."
        exit 0
    fi
    
    log_message "Changes detected in repository. Starting deployment..."
    log_message "Last known commit: $LAST_COMMIT"
    log_message "Latest commit: $LATEST_COMMIT"
    
    # Check each file for changes
    changes_detected=false
    
    for file in "${FILES_TO_CHECK[@]}"; do
        download_and_check "$file"
        result=$?
        
        if [ $result -eq 2 ]; then
            changes_detected=true
        elif [ $result -eq 1 ]; then
            log_message "WARNING: Failed to check $file"
        fi
    done
    
    if [ "$changes_detected" = true ]; then
        log_message "File changes detected. Proceeding with container update..."
        
        # Rebuild Docker image with latest code
        if rebuild_image; then
            # Restart container with new image
            if restart_container; then
                log_message "Deployment completed successfully"
                
                # Wait a few seconds and verify container is running
                sleep 5
                if is_container_running; then
                    log_message "Container health check: PASSED"
                    # Update the last commit file
                    echo "$LATEST_COMMIT" > "$LAST_COMMIT_FILE"
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
        log_message "No file changes detected, but commit hash changed. Updating commit reference."
        echo "$LATEST_COMMIT" > "$LAST_COMMIT_FILE"
    fi
    
    log_message "Auto-deployment completed successfully"
}

# Run main function
main "$@"
