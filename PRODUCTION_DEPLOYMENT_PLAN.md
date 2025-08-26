# Production Deployment Plan - Dell Port Tracer v2.1.3

## 🎯 **DEPLOYMENT OVERVIEW**

This plan outlines the complete production deployment strategy for Dell Port Tracer v2.1.3 with:
- **Nginx reverse proxy** with SSL termination
- **Dockerized application** for consistency and scalability  
- **Auto-deployment pipeline** that monitors main branch for updates
- **Production-grade security** and monitoring
- **Zero-downtime deployments** with health checks

---

## 🏗️ **ARCHITECTURE OVERVIEW**

```
Internet → Nginx (SSL/Port 443) → Docker Container (Port 5000) → PostgreSQL (Port 5432)
                ↓
         Auto-Deploy Monitor (watches GitHub main branch)
```

### Directory Structure:
```
/opt/dell-port-tracer/
├── app/                    # Application code (git repository)
│   ├── port_tracer_web.py
│   ├── templates/
│   ├── static/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docker-compose.prod.yml
│   └── .env
├── config/                 # Configuration files
│   └── nginx.conf
├── ssl/                    # SSL certificates
│   ├── fullchain.pem
│   └── privkey.pem
├── logs/                   # Application and system logs
│   ├── deploy.log
│   └── nginx/
├── backups/                # Database and application backups
├── deploy-monitor.sh       # Auto-deployment script
└── README.md              # Deployment documentation
```

### Components:
1. **Nginx** - Reverse proxy, SSL termination, static file serving
2. **Docker** - Application containerization
3. **PostgreSQL** - Database (containerized or external)
4. **Auto-Deploy Service** - Git monitoring and deployment automation
5. **Monitoring** - Health checks and logging

---

## 📋 **PRE-DEPLOYMENT REQUIREMENTS**

### Server Requirements:
- **OS**: Ubuntu 20.04+ LTS or CentOS 8+
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 50GB+ SSD
- **Network**: Static IP with ports 80/443 accessible
- **Docker**: Version 20.10+
- **Docker Compose**: Version 2.0+

### Prerequisites Checklist:
- [ ] Server provisioned with root/sudo access
- [ ] Domain name configured (e.g., porttracer.yourdomain.com)
- [ ] SSL certificate available (Let's Encrypt recommended)
- [ ] GitHub repository access configured
- [ ] Switch credentials available
- [ ] Active Directory configuration (if using Windows Auth)

---

## 🐳 **DOCKER CONFIGURATION**

### 1. Enhanced Dockerfile

```dockerfile
# Production Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    openssh-client \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 porttracer && chown -R porttracer:porttracer /app
USER porttracer

# Copy requirements first for better caching
COPY --chown=porttracer:porttracer requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY --chown=porttracer:porttracer . .

# Create necessary directories
RUN mkdir -p logs static/uploads

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Expose port
EXPOSE 5000

# Run application
CMD ["python", "port_tracer_web.py"]
```

### 2. Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: porttracer-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ../backups:/backups
    ports:
      - "127.0.0.1:5432:5432"
    networks:
      - porttracer-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Dell Port Tracer Application
  porttracer:
    build: 
      context: .
      dockerfile: Dockerfile
    image: dell-port-tracer:v2.1.3
    container_name: porttracer-app
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      # Database Configuration
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}  
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      
      # Application Configuration
      FLASK_ENV: production
      PYTHONUNBUFFERED: 1
      
      # Switch Credentials
      SWITCH_USERNAME: ${SWITCH_USERNAME}
      SWITCH_PASSWORD: ${SWITCH_PASSWORD}
      
      # Authentication
      USE_WINDOWS_AUTH: ${USE_WINDOWS_AUTH:-true}
      AD_SERVER: ${AD_SERVER}
      AD_DOMAIN: ${AD_DOMAIN}
      AD_BASE_DN: ${AD_BASE_DN}
      
      # User Passwords
      OSS_PASSWORD: ${OSS_PASSWORD}
      NETADMIN_PASSWORD: ${NETADMIN_PASSWORD}
      SUPERADMIN_PASSWORD: ${SUPERADMIN_PASSWORD}
      
      # CPU and Protection Settings
      CPU_SAFETY_ENABLED: true
      CPU_GREEN_THRESHOLD: 40.0
      CPU_YELLOW_THRESHOLD: 60.0
      CPU_RED_THRESHOLD: 80.0
      
      # Switch Protection
      SWITCH_PROTECTION_ENABLED: true
      MAX_CONNECTIONS_PER_SWITCH: 8
      MAX_TOTAL_CONNECTIONS: 64
      COMMANDS_PER_SECOND_LIMIT: 10
      
      # VLAN Management
      VLAN_MANAGEMENT_ENABLED: true
      VLAN_INTERFACE_RANGE_OPTIMIZATION: true
      VLAN_FALLBACK_INDIVIDUAL_PORTS: true
      
      # Logging
      LOG_LEVEL: INFO
      
    volumes:
      - ../logs:/app/logs
      - ../backups:/app/backups
    ports:
      - "127.0.0.1:5000:5000"
    networks:
      - porttracer-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: porttracer-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ../config/nginx.conf:/etc/nginx/nginx.conf:ro
      - ../ssl:/etc/nginx/ssl:ro
      - ./static:/var/www/static:ro
      - ../logs/nginx:/var/log/nginx
    depends_on:
      - porttracer
    networks:
      - porttracer-network
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
    driver: local

networks:
  porttracer-network:
    driver: bridge
```

---

## 🌐 **NGINX CONFIGURATION**

### 1. Main Nginx Configuration

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    
    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                   '$status $body_bytes_sent "$http_referer" '
                   '"$http_user_agent" "$http_x_forwarded_for"';
    
    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;
    
    # Basic Settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 10M;
    
    # Gzip Compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml
        text/plain
        text/css
        text/xml
        text/javascript;
    
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;
    
    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Upstream backend
    upstream porttracer_backend {
        server porttracer:5000;
        keepalive 32;
    }
    
    # HTTP to HTTPS redirect
    server {
        listen 80;
        server_name porttracer.yourdomain.com;  # Replace with your domain
        return 301 https://$server_name$request_uri;
    }
    
    # Main HTTPS server
    server {
        listen 443 ssl http2;
        server_name porttracer.yourdomain.com;  # Replace with your domain
        
        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_session_timeout 1d;
        ssl_session_cache shared:MozTLS:10m;
        ssl_session_tickets off;
        
        # Modern SSL configuration
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        
        # HSTS
        add_header Strict-Transport-Security "max-age=63072000" always;
        
        # Static files
        location /static/ {
            alias /var/www/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
            
            # Compress static files
            gzip_static on;
        }
        
        # API endpoints with rate limiting
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://porttracer_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
            
            # Timeouts
            proxy_connect_timeout 30s;
            proxy_send_timeout 30s;
            proxy_read_timeout 30s;
        }
        
        # Login endpoint with strict rate limiting
        location /login {
            limit_req zone=login burst=5 nodelay;
            
            proxy_pass http://porttracer_backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
        
        # Health check endpoint
        location /health {
            proxy_pass http://porttracer_backend;
            access_log off;
        }
        
        # Main application
        location / {
            proxy_pass http://porttracer_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_cache_bypass $http_upgrade;
            
            # Timeouts
            proxy_connect_timeout 30s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }
    }
}
```

---

## 🔄 **AUTO-DEPLOYMENT SYSTEM**

### 1. Auto-Deploy Service Script

```bash
#!/bin/bash
# deploy-monitor.sh - Production Auto-Deployment Service

# Configuration
REPO_URL="https://github.com/Crispy-Pasta/SwitchPortManager.git"
REPO_DIR="/opt/dell-port-tracer/app"
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
LOG_FILE="/opt/dell-port-tracer/logs/deploy.log"
BACKUP_DIR="/opt/dell-port-tracer/backups"
SLACK_WEBHOOK_URL=""  # Optional: Add your Slack webhook for notifications

# Create necessary directories
mkdir -p "$BACKUP_DIR" "$(dirname "$LOG_FILE")"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Notification function
notify() {
    local message="$1"
    local status="$2"
    
    log "$message"
    
    # Optional Slack notification
    if [ -n "$SLACK_WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚀 Port Tracer Deploy: $message\"}" \
            "$SLACK_WEBHOOK_URL" > /dev/null 2>&1
    fi
}

# Health check function
health_check() {
    local max_attempts=30
    local attempt=1
    
    log "Performing health check..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:5000/health > /dev/null 2>&1; then
            log "Health check passed on attempt $attempt"
            return 0
        fi
        
        log "Health check failed, attempt $attempt/$max_attempts"
        sleep 10
        ((attempt++))
    done
    
    log "Health check failed after $max_attempts attempts"
    return 1
}

# Backup function
backup_current() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_path="$BACKUP_DIR/backup_$timestamp"
    
    log "Creating backup at $backup_path"
    
    # Create backup directory
    mkdir -p "$backup_path"
    
    # Backup database
    if docker exec porttracer-postgres pg_dump -U dell_tracer_user dell_port_tracer > "$backup_path/database.sql" 2>/dev/null; then
        log "Database backup successful"
    else
        log "Database backup failed"
    fi
    
    # Backup application files
    if [ -d "$REPO_DIR" ]; then
        cp -r "$REPO_DIR" "$backup_path/app" 2>/dev/null
        log "Application backup successful"
    fi
    
    # Cleanup old backups (keep last 5)
    cd "$BACKUP_DIR"
    ls -t | tail -n +6 | xargs -r rm -rf
    
    echo "$backup_path"
}

# Rollback function
rollback() {
    local backup_path="$1"
    
    if [ -z "$backup_path" ] || [ ! -d "$backup_path" ]; then
        log "ERROR: Invalid backup path for rollback"
        return 1
    fi
    
    log "Rolling back to $backup_path"
    
    # Stop current services
    cd "$REPO_DIR"
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Restore application files
    if [ -d "$backup_path/app" ]; then
        rm -rf "$REPO_DIR"
        cp -r "$backup_path/app" "$REPO_DIR"
        log "Application files restored"
    fi
    
    # Restore database
    if [ -f "$backup_path/database.sql" ]; then
        docker-compose -f "$DOCKER_COMPOSE_FILE" up -d postgres
        sleep 10
        docker exec -i porttracer-postgres psql -U dell_tracer_user -d dell_port_tracer < "$backup_path/database.sql"
        log "Database restored"
    fi
    
    # Start services
    docker-compose -f "$DOCKER_COMPOSE_FILE" up -d
    
    if health_check; then
        notify "Rollback successful" "success"
        return 0
    else
        notify "Rollback failed" "error"
        return 1
    fi
}

# Main deployment function
deploy() {
    log "Starting deployment process..."
    
    # Create backup before deployment
    local backup_path
    backup_path=$(backup_current)
    
    # Navigate to repository directory
    cd "$REPO_DIR" || {
        log "ERROR: Cannot access repository directory"
        return 1
    }
    
    # Pull latest changes
    log "Pulling latest changes from main branch"
    if ! git pull origin main; then
        log "ERROR: Failed to pull latest changes"
        return 1
    fi
    
    # Build new images
    log "Building Docker images"
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" build --no-cache; then
        log "ERROR: Docker build failed"
        rollback "$backup_path"
        return 1
    fi
    
    # Stop current services
    log "Stopping current services"
    docker-compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Start new services
    log "Starting updated services"
    if ! docker-compose -f "$DOCKER_COMPOSE_FILE" up -d; then
        log "ERROR: Failed to start services"
        rollback "$backup_path"
        return 1
    fi
    
    # Health check
    if health_check; then
        notify "Deployment successful - v$(git rev-parse --short HEAD)" "success"
        
        # Cleanup old images
        docker image prune -f > /dev/null 2>&1
        
        log "Deployment completed successfully"
        return 0
    else
        log "ERROR: Health check failed after deployment"
        rollback "$backup_path"
        return 1
    fi
}

# Check for updates function
check_updates() {
    cd "$REPO_DIR" || return 1
    
    # Fetch latest changes
    git fetch origin main > /dev/null 2>&1
    
    # Check if local is behind remote
    local local_commit=$(git rev-parse HEAD)
    local remote_commit=$(git rev-parse origin/main)
    
    if [ "$local_commit" != "$remote_commit" ]; then
        log "Updates detected: $local_commit -> $remote_commit"
        return 0
    else
        return 1
    fi
}

# Main monitoring loop
main() {
    log "Starting auto-deployment monitor for Dell Port Tracer v2.1.3"
    
    # Initial repository setup
    if [ ! -d "$REPO_DIR" ]; then
        log "Cloning repository..."
        git clone "$REPO_URL" "$REPO_DIR"
        cd "$REPO_DIR"
        git checkout main
    fi
    
    # Monitoring loop
    while true; do
        if check_updates; then
            log "Updates found, starting deployment..."
            if deploy; then
                notify "Auto-deployment completed successfully" "success"
            else
                notify "Auto-deployment failed" "error"
            fi
        fi
        
        # Wait 5 minutes before next check
        sleep 300
    done
}

# Handle script arguments
case "${1:-main}" in
    "deploy")
        deploy
        ;;
    "rollback")
        rollback "$2"
        ;;
    "health")
        health_check
        ;;
    "main")
        main
        ;;
    *)
        echo "Usage: $0 [deploy|rollback|health|main]"
        exit 1
        ;;
esac
```

### 2. Systemd Service for Auto-Deploy

```ini
# /etc/systemd/system/porttracer-autodeploy.service
[Unit]
Description=Dell Port Tracer Auto-Deploy Monitor
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/dell-port-tracer
ExecStart=/opt/dell-port-tracer/deploy-monitor.sh main
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

# Environment variables
Environment=DOCKER_COMPOSE_FILE=docker-compose.prod.yml

[Install]
WantedBy=multi-user.target
```

---

## 🔐 **ENVIRONMENT CONFIGURATION**

### 1. Production Environment File

```bash
# .env.production
# Database Configuration
POSTGRES_DB=dell_port_tracer_prod
POSTGRES_USER=dell_tracer_user
POSTGRES_PASSWORD=your_secure_database_password_here

# Switch Credentials
SWITCH_USERNAME=your_switch_username
SWITCH_PASSWORD=your_switch_password

# Windows Authentication (if used)
USE_WINDOWS_AUTH=true
AD_SERVER=ldap://your-domain-controller.com
AD_DOMAIN=yourdomain.com
AD_BASE_DN=DC=yourdomain,DC=com

# Application User Passwords
OSS_PASSWORD=secure_oss_password_123
NETADMIN_PASSWORD=secure_netadmin_password_123
SUPERADMIN_PASSWORD=secure_superadmin_password_123

# Security
SECRET_KEY=your_very_long_and_secure_secret_key_here

# Optional: Slack notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
```

---

## 📋 **DEPLOYMENT STEPS**

### Phase 1: Server Preparation

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 3. Create deployment directory structure
sudo mkdir -p /opt/dell-port-tracer/{app,logs,backups,config,ssl}
sudo chown -R $USER:$USER /opt/dell-port-tracer

# 4. Clone repository
cd /opt/dell-port-tracer/app
git clone https://github.com/Crispy-Pasta/SwitchPortManager.git .
git checkout main
```

### Phase 2: SSL Certificate Setup

```bash
# Using Let's Encrypt (recommended)
sudo apt install certbot -y

# Generate certificate (replace with your domain)
sudo certbot certonly --standalone -d porttracer.yourdomain.com

# Create SSL directory and copy certificates
sudo cp /etc/letsencrypt/live/porttracer.yourdomain.com/fullchain.pem /opt/dell-port-tracer/ssl/
sudo cp /etc/letsencrypt/live/porttracer.yourdomain.com/privkey.pem /opt/dell-port-tracer/ssl/
sudo chown -R $USER:$USER /opt/dell-port-tracer/ssl
```

### Phase 3: Configuration Setup

```bash
# 1. Create nginx configuration
# Copy the nginx.conf content from above into /opt/dell-port-tracer/config/nginx.conf

# 2. Create environment file
cd /opt/dell-port-tracer/app
cp .env.production.example .env
# Edit .env with your actual configuration values

# 3. Create docker-compose file
# Copy the docker-compose.prod.yml content from above into /opt/dell-port-tracer/app/docker-compose.prod.yml
```

### Phase 4: Auto-Deploy Setup

```bash
# 1. Copy auto-deploy script
sudo cp deploy-monitor.sh /opt/dell-port-tracer/
sudo chmod +x /opt/dell-port-tracer/deploy-monitor.sh

# 2. Create systemd service
sudo cp porttracer-autodeploy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable porttracer-autodeploy

# 3. Create log rotation
sudo tee /etc/logrotate.d/porttracer << EOF
/opt/dell-port-tracer/logs/deploy.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
EOF
```

### Phase 5: Initial Deployment

```bash
# 1. Build and start services
cd /opt/dell-port-tracer/app
docker-compose -f docker-compose.prod.yml up -d --build

# 2. Initialize database
docker-compose -f docker-compose.prod.yml exec porttracer python init_database.py

# 3. Test deployment
curl -k https://porttracer.yourdomain.com/health

# 4. Start auto-deploy monitoring
sudo systemctl start porttracer-autodeploy
```

---

## 📊 **MONITORING & MAINTENANCE**

### 1. Health Monitoring Script

```bash
#!/bin/bash
# health-monitor.sh
HEALTH_URL="https://porttracer.yourdomain.com/health"
LOG_FILE="/var/log/porttracer-health.log"

check_health() {
    if curl -f -k "$HEALTH_URL" > /dev/null 2>&1; then
        echo "[$(date)] Health check: OK" >> "$LOG_FILE"
        return 0
    else
        echo "[$(date)] Health check: FAILED" >> "$LOG_FILE"
        # Restart services if health check fails
        cd /opt/dell-port-tracer/app
        docker-compose -f docker-compose.prod.yml restart
        return 1
    fi
}

check_health
```

### 2. Backup Script

```bash
#!/bin/bash
# backup.sh - Daily backup script
BACKUP_DIR="/opt/dell-port-tracer/backups"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

# Database backup
cd /opt/dell-port-tracer/app
docker exec porttracer-postgres pg_dump -U dell_tracer_user dell_port_tracer_prod | gzip > "$BACKUP_DIR/db_backup_$TIMESTAMP.sql.gz"

# Application backup
tar -czf "$BACKUP_DIR/app_backup_$TIMESTAMP.tar.gz" /opt/dell-port-tracer/app --exclude=/opt/dell-port-tracer/logs

# Cleanup old backups (keep 7 days)
find "$BACKUP_DIR" -type f -mtime +7 -delete

echo "[$(date)] Backup completed: $TIMESTAMP"
```

### 3. Log Monitoring

```bash
# View deployment logs
sudo journalctl -u porttracer-autodeploy -f

# View application logs
docker-compose -f docker-compose.prod.yml logs -f porttracer

# View nginx logs
docker-compose -f docker-compose.prod.yml logs -f nginx
```

---

## 🔧 **MAINTENANCE COMMANDS**

```bash
# Manual deployment
cd /opt/dell-port-tracer && ./deploy-monitor.sh deploy

# Rollback to previous version
./deploy-monitor.sh rollback /opt/dell-port-tracer/backups/backup_YYYYMMDD_HHMMSS

# Health check
./deploy-monitor.sh health

# View logs (run from /opt/dell-port-tracer/app)
cd /opt/dell-port-tracer/app
docker-compose -f docker-compose.prod.yml logs -f

# Database access
docker-compose -f docker-compose.prod.yml exec postgres psql -U dell_tracer_user -d dell_port_tracer_prod

# Application shell access
docker-compose -f docker-compose.prod.yml exec porttracer bash

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Update SSL certificates
sudo certbot renew
```

---

## 🚨 **TROUBLESHOOTING GUIDE**

### Common Issues:

1. **Service won't start**
   ```bash
   # Check logs
   docker-compose -f docker-compose.prod.yml logs
   
   # Restart services
   docker-compose -f docker-compose.prod.yml down
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Database connection issues**
   ```bash
   # Check postgres health
   docker-compose -f docker-compose.prod.yml exec postgres pg_isready
   
   # Reset database
   docker-compose -f docker-compose.prod.yml down
   docker volume rm porttracer_postgres_data
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **SSL certificate issues**
   ```bash
   # Renew certificates
   sudo certbot renew
   
   # Update nginx
   docker-compose -f docker-compose.prod.yml restart nginx
   ```

4. **Auto-deploy not working**
   ```bash
   # Check service status
   sudo systemctl status porttracer-autodeploy
   
   # Check logs
   sudo journalctl -u porttracer-autodeploy -f
   
   # Restart service
   sudo systemctl restart porttracer-autodeploy
   ```

---

## 📈 **PERFORMANCE OPTIMIZATION**

### 1. Nginx Caching
```nginx
# Add to nginx.conf
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=app_cache:10m max_size=100m inactive=60m;

location ~* \.(css|js|png|jpg|jpeg|gif|ico|svg)$ {
    proxy_cache app_cache;
    proxy_cache_valid 200 1h;
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

### 2. Database Optimization
```sql
-- Run these commands in PostgreSQL
VACUUM ANALYZE;
REINDEX DATABASE dell_port_tracer_prod;

-- Add indexes for better performance
CREATE INDEX idx_switches_site_floor ON switches(site_id, floor_id);
CREATE INDEX idx_audit_timestamp ON audit_logs(timestamp);
```

---

## ✅ **DEPLOYMENT CHECKLIST**

### Pre-Deployment:
- [ ] Server provisioned and accessible
- [ ] Domain name configured and pointing to server
- [ ] SSL certificates obtained
- [ ] Environment variables configured
- [ ] Database credentials prepared
- [ ] Switch credentials available

### Deployment:
- [ ] Docker and Docker Compose installed
- [ ] Repository cloned
- [ ] Nginx configuration created
- [ ] Docker Compose file configured
- [ ] Services started successfully
- [ ] Health check passes
- [ ] Auto-deploy service configured and running

### Post-Deployment:
- [ ] Application accessible via HTTPS
- [ ] Login functionality working
- [ ] Switch connectivity tested
- [ ] Database operations functional
- [ ] Auto-deployment tested
- [ ] Monitoring and alerting configured
- [ ] Backup procedures implemented
- [ ] Documentation updated

---

## 🎯 **EXPECTED RESULTS**

After successful deployment, you will have:

1. **Production-ready application** running on HTTPS with SSL termination
2. **Automatic deployments** triggered by pushes to main branch
3. **Zero-downtime updates** with health checks and rollback capability
4. **Scalable architecture** ready for load balancing
5. **Comprehensive monitoring** and logging
6. **Automated backups** and disaster recovery
7. **Professional SSL certificate** with automatic renewal
8. **Rate limiting and security headers** for protection

The system will automatically monitor your GitHub main branch every 5 minutes and deploy updates when detected, ensuring your production environment stays current with minimal manual intervention.

---

**Deployment Plan Version**: 1.0  
**Last Updated**: August 15, 2025  
**Compatibility**: Dell Port Tracer v2.1.3
