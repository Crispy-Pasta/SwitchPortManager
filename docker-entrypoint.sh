#!/bin/bash
set -e

# =================================================================
# Dell Switch Port Tracer - Docker Entrypoint Script
# =================================================================
# This script initializes the database and starts the application
# in a containerized environment with proper error handling.

# Get version dynamically from the application
APP_VERSION=$(python get_version.py 2>/dev/null || echo "Unknown")
echo "🚀 Starting Dell Switch Port Tracer v${APP_VERSION}..."
echo "=================================================="

# Function to log messages with timestamps
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

log "🔍 Environment check..."

# Verify Python is available
if ! command_exists python; then
    log "❌ Python not found in container"
    exit 1
fi

# Verify main application file exists
if [ ! -f "/app/wsgi.py" ] && [ ! -f "/app/run.py" ]; then
    log "❌ Main application file not found (wsgi.py or run.py)"
    exit 1
fi

# Show environment configuration (mask sensitive values)
log "📋 Configuration:"
log "   • Database Host: ${POSTGRES_HOST:-localhost}"
log "   • Database Name: ${POSTGRES_DB:-port_tracer_db}"
log "   • Database User: ${POSTGRES_USER:-dell_tracer_user}"
log "   • Switch Username: ${SWITCH_USERNAME:-NOT_SET}"
log "   • Session Timeout: ${PERMANENT_SESSION_LIFETIME:-5} minutes"
log "   • Session Cookie Secure: ${SESSION_COOKIE_SECURE:-true}"

# Optional: Initialize database if init script exists
if [ -f "/app/init_db.py" ] || [ -f "/app/app/core/init_db.py" ]; then
    log "🏗️  Initializing database schema..."
    if [ -f "/app/init_db.py" ]; then
        if python init_db.py; then
            log "✅ Database initialization completed successfully"
        else
            log "⚠️  Database initialization failed - continuing anyway (might already be initialized)"
        fi
    elif [ -f "/app/app/core/init_db.py" ]; then
        if python app/core/init_db.py; then
            log "✅ Database initialization completed successfully"
        else
            log "⚠️  Database initialization failed - continuing anyway (might already be initialized)"
        fi
    fi
else
    log "ℹ️  No database initialization script found - skipping database setup"
fi

# Optional: Run database migrations if they exist
if [ -f "/app/migrate_db.py" ]; then
    log "🔄 Running database migrations..."
    python migrate_db.py
fi

# Start the application
log "🌐 Starting Dell Switch Port Tracer web application..."
log "📊 Web Interface will be available at http://localhost:5000"
log "🔐 Default users:"
log "   • admin / password (SuperAdmin)"
log "   • netadmin / netadmin123 (NetAdmin)"
log "   • superadmin / superadmin123 (SuperAdmin)"
log "=================================================="

# Execute the main application
# Use Gunicorn for production deployment
if [ "${ENVIRONMENT:-production}" = "development" ]; then
    log "🔧 Starting in DEVELOPMENT mode with Flask dev server"
    exec python run.py
else
    log "🚀 Starting in PRODUCTION mode with Gunicorn"
    exec gunicorn --workers 1 --bind 0.0.0.0:5000 --timeout 180 --access-logfile - --error-logfile - wsgi:application
fi
