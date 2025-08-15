#!/bin/bash

# Safe Dell Port Tracer Deployment Script for Repository
# This is the template version - copy to production server

# Safe Dell Port Tracer Deployment Script
# Protects configuration and database data during updates

set -e  # Exit on any error

# Configuration
DEPLOY_DIR="/opt/dell-port-tracer"
BACKUP_DIR="$DEPLOY_DIR/backups"
DATA_DIR="$DEPLOY_DIR/data"
LOG_FILE="$DEPLOY_DIR/logs/deployment.log"
COMPOSE_FILE="docker-compose.prod.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages with timestamp
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

# Function to create backup of critical files
backup_critical_files() {
    local backup_timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_path="$BACKUP_DIR/deployment_$backup_timestamp"
    
    log_message "INFO" "Creating backup: $backup_path"
    mkdir -p "$backup_path"
    
    # Backup environment files
    if [ -f "$DATA_DIR/.env.production" ]; then
        cp "$DATA_DIR/.env.production" "$backup_path/"
        log_message "INFO" "Backed up .env.production"
    fi
    
    # Backup Docker Compose file
    if [ -f "$DEPLOY_DIR/$COMPOSE_FILE" ]; then
        cp "$DEPLOY_DIR/$COMPOSE_FILE" "$backup_path/"
        log_message "INFO" "Backed up $COMPOSE_FILE"
    fi
    
    # Backup database
    if docker ps --format "{{.Names}}" | grep -q "dell-port-tracer-postgres"; then
        log_message "INFO" "Creating database backup..."
        docker exec dell-port-tracer-postgres pg_dump -U porttracer_user port_tracer_db > "$backup_path/database_backup.sql"
        log_message "INFO" "Database backup created"
    fi
    
    # Backup switch inventory if exists
    if [ -f "$DATA_DIR/switches.json" ]; then
        cp "$DATA_DIR/switches.json" "$backup_path/"
        log_message "INFO" "Backed up switches.json"
    fi
    
    echo "$backup_path" > "$DEPLOY_DIR/.last_backup"
    log_message "INFO" "Backup completed: $backup_path"
}

# Function to protect critical data
protect_data() {
    log_message "INFO" "Protecting critical data files..."
    
    # Ensure data directory exists and is protected
    mkdir -p "$DATA_DIR"
    chmod 755 "$DATA_DIR"
    
    # Protect environment file
    if [ -f "$DEPLOY_DIR/.env" ] && [ ! -f "$DATA_DIR/.env.production" ]; then
        log_message "INFO" "Moving .env to protected location"
        mv "$DEPLOY_DIR/.env" "$DATA_DIR/.env.production"
        chmod 600 "$DATA_DIR/.env.production"
    fi
    
    # Protect SSL directory if exists
    if [ -d "$DEPLOY_DIR/ssl" ] && [ ! -d "$DATA_DIR/ssl" ]; then
        log_message "INFO" "Moving SSL certificates to protected location"
        mv "$DEPLOY_DIR/ssl" "$DATA_DIR/"
        chmod -R 600 "$DATA_DIR/ssl"
    fi
    
    log_message "INFO" "Data protection completed"
}

# Function to check database volume consistency
check_database_volumes() {
    log_message "INFO" "Checking database volume consistency..."
    
    # List all postgres volumes
    local volumes=$(docker volume ls --format "{{.Name}}" | grep postgres)
    log_message "DEBUG" "Found postgres volumes: $volumes"
    
    # Check if we have multiple conflicting volumes
    local volume_count=$(echo "$volumes" | wc -l)
    if [ "$volume_count" -gt 1 ]; then
        log_message "WARN" "Multiple postgres volumes detected!"
        log_message "WARN" "This may cause data loss between deployments"
        echo "$volumes" | while read volume; do
            local created=$(docker volume inspect "$volume" --format "{{.CreatedAt}}")
            log_message "WARN" "Volume: $volume, Created: $created"
        done
    fi
    
    # Ensure we're using the consistent named volume
    if ! docker volume ls --format "{{.Name}}" | grep -q "dell_port_tracer_postgres_data"; then
        log_message "INFO" "Creating consistent named volume for database"
        docker volume create dell_port_tracer_postgres_data
    fi
}

# Function to validate deployment
validate_deployment() {
    log_message "INFO" "Validating deployment configuration..."
    
    # Check if data directory exists
    if [ ! -d "$DATA_DIR" ]; then
        log_message "ERROR" "Protected data directory not found: $DATA_DIR"
        return 1
    fi
    
    # Check if environment file exists
    if [ ! -f "$DATA_DIR/.env.production" ]; then
        log_message "ERROR" "Protected environment file not found: $DATA_DIR/.env.production"
        return 1
    fi
    
    # Check Docker Compose file
    if [ ! -f "$DEPLOY_DIR/$COMPOSE_FILE" ]; then
        log_message "ERROR" "Docker Compose file not found: $COMPOSE_FILE"
        return 1
    fi
    
    # Validate Docker Compose configuration
    if ! docker-compose -f "$DEPLOY_DIR/$COMPOSE_FILE" config >/dev/null 2>&1; then
        log_message "ERROR" "Docker Compose configuration is invalid"
        return 1
    fi
    
    log_message "INFO" "Deployment validation passed"
    return 0
}

# Function to deploy with data protection
safe_deploy() {
    log_message "INFO" "Starting safe deployment..."
    
    cd "$DEPLOY_DIR"
    
    # Use Docker Compose for consistent deployment
    log_message "INFO" "Stopping services gracefully..."
    docker-compose -f "$COMPOSE_FILE" down
    
    # Build new images if needed
    log_message "INFO" "Building application image..."
    docker-compose -f "$COMPOSE_FILE" build app
    
    # Start services
    log_message "INFO" "Starting services with protected data..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    # Wait for services to be healthy
    log_message "INFO" "Waiting for services to become healthy..."
    local max_wait=60
    local wait_time=0
    
    while [ $wait_time -lt $max_wait ]; do
        if docker-compose -f "$COMPOSE_FILE" ps | grep -q "healthy"; then
            log_message "INFO" "Services are healthy"
            break
        fi
        sleep 5
        wait_time=$((wait_time + 5))
    done
    
    if [ $wait_time -ge $max_wait ]; then
        log_message "ERROR" "Services failed to become healthy within $max_wait seconds"
        return 1
    fi
    
    log_message "INFO" "Safe deployment completed successfully"
    return 0
}

# Function to display deployment summary
deployment_summary() {
    log_message "INFO" "=== DEPLOYMENT SUMMARY ==="
    
    # Service status
    docker-compose -f "$DEPLOY_DIR/$COMPOSE_FILE" ps
    
    # Volume information
    log_message "INFO" "Database volume status:"
    docker volume ls | grep postgres
    
    # Protected files status
    log_message "INFO" "Protected files:"
    ls -la "$DATA_DIR/" 2>/dev/null || log_message "WARN" "Data directory not accessible"
    
    # Last backup location
    if [ -f "$DEPLOY_DIR/.last_backup" ]; then
        local last_backup=$(cat "$DEPLOY_DIR/.last_backup")
        log_message "INFO" "Last backup: $last_backup"
    fi
    
    log_message "INFO" "=== END SUMMARY ==="
}

# Main function
main() {
    log_message "INFO" "🚀 Starting Safe Dell Port Tracer Deployment"
    log_message "INFO" "Deploy Directory: $DEPLOY_DIR"
    log_message "INFO" "Data Protection: ENABLED"
    
    # Ensure we're in the correct directory
    cd "$DEPLOY_DIR"
    
    # Create necessary directories
    mkdir -p "$BACKUP_DIR" "$DATA_DIR" "$(dirname "$LOG_FILE")"
    
    # Step 1: Backup critical files
    backup_critical_files
    
    # Step 2: Protect critical data
    protect_data
    
    # Step 3: Check database consistency
    check_database_volumes
    
    # Step 4: Validate deployment
    if ! validate_deployment; then
        log_message "ERROR" "Deployment validation failed"
        exit 1
    fi
    
    # Step 5: Safe deployment
    if ! safe_deploy; then
        log_message "ERROR" "Deployment failed"
        exit 1
    fi
    
    # Step 6: Summary
    deployment_summary
    
    log_message "INFO" "🎉 Safe deployment completed successfully!"
    log_message "INFO" "🔒 Your configuration and database data are protected"
    log_message "INFO" "🌐 Application URL: https://$(hostname -I | awk '{print $1}')"
}

# Script entry point
case "${1:-}" in
    "--help"|"-h")
        echo "Safe Dell Port Tracer Deployment Script"
        echo ""
        echo "Features:"
        echo "  🔒 Protects configuration files (.env, switches.json)"
        echo "  💾 Preserves database data between deployments"
        echo "  📦 Creates automatic backups before deployment"
        echo "  ✅ Validates deployment configuration"
        echo "  🔄 Uses consistent Docker Compose deployment"
        echo ""
        echo "Usage: $0 [--help]"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac
