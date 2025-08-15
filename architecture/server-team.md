# Dell Port Tracer - Server Team Architecture

## 🖥️ Server Team Overview

This documentation provides an overview of the server and infrastructure-related aspects of the Dell Port Tracer application, including deployment architecture, server components, monitoring, maintenance, and security.

## Server Architecture Diagram (v2.1.3)

```
┌─────────────────────────────────────────────────────────────────┐
│             PRODUCTION SERVER ARCHITECTURE v2.1.3              │
└─────────────────────────────────────────────────────────────────┘

                  User Workstations
                  ┌──────────────┐
                  │              │
                  │  Web Browser │ ◄── HTTPS (Port 443)
                  │              │ ◄── HTTP (Port 80) → Redirect to HTTPS
                  └───────┬──────┘
                          │
                          │ SSL/TLS Encrypted
                          │
                          ▼
                ┌─────────────────┐
                │  Linux Server   │ ◄───────────────────────────── Windows AD
                │  (Production)   │          LDAP Authentication   (Optional)
                └─────────┬───────┘                 (Port 389/636)
                          │
                          │ Docker Compose Production Stack
                          ▼
          ┌──────────────────────────────────────────┐
          │            Docker Network                │
          │         (dell-port-tracer)               │
          ├──────────────────────────────────────────┤
          │                                          │
          │  ┌─────────────────────────────────────┐ │
          │  │     dell-port-tracer-nginx          │ │
          │  │    • SSL/HTTPS Termination          │ │
          │  │    • Reverse Proxy                  │ │
          │  │    • Security Headers               │ │
          │  │    • Ports: 80:80, 443:443          │ │
          │  │    • Self-signed SSL Certs          │ │
          │  └─────────────┬───────────────────────┘ │
          │                │                         │
          │                ▼                         │
          │  ┌─────────────────────────────────────┐ │
          │  │     dell-port-tracer-app            │ │
          │  │    • Flask Application Server       │ │
          │  │    • Port Tracing Logic              │ │
          │  │    • SSH to Dell Switches           │ │
          │  │    • Internal Port: 5000             │ │
          │  │    • Health Checks: /health          │ │
          │  └─────────────┬───────────────────────┘ │
          │                │                         │
          │                ▼                         │
          │  ┌─────────────────────────────────────┐ │
          │  │   dell-port-tracer-postgres         │ │
          │  │    • PostgreSQL Database            │ │
          │  │    • Persistent Named Volume        │ │
          │  │    • Automatic Backups              │ │
          │  │    • Internal Port: 5432             │ │
          │  │    • Health Checks: pg_isready      │ │
          │  └─────────────────────────────────────┘ │
          └──────────────────────────────────────────┘

          ┌──────────────────────────────────────────┐
          │           Persistent Storage             │
          ├──────────────────────────────────────────┤
          │  • dell_port_tracer_postgres_data        │
          │  • ./logs/nginx (bind mount)             │
          │  • ./logs/app (bind mount)               │
          │  • ./backups (bind mount)                │
          └──────────────────────────────────────────┘

          ┌──────────────────────────────────────────┐
          │         External Connections             │
          ├──────────────────────────────────────────┤
          │  Dell Switches ◄── SSH (Port 22)        │
          │  Windows AD    ◄── LDAP (389/636)       │
          │  Syslog Server ◄── UDP (Port 514)       │
          └──────────────────────────────────────────┘
```

## Deployment Architecture

- **Containerization**:
  - Deployed entirely in Docker containers.
  - Docker Compose used for orchestration.
  - Separate containers for the web application, database, and other services.

- **Reverse Proxy**:
  - nginx serves as the reverse proxy for SSL termination and load balancing.
  - Configured to forward requests to the Flask application container.

- **Database**:
  - PostgreSQL used for persistent data storage.
  - Secured with user authentication.

- **Authentication**:
  - Integrates with Windows Active Directory for user authentication via LDAP.

## Container Architecture Details

### Docker Compose Services (v2.1.3)

```yaml
# docker-compose.prod.yml - Production Configuration
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: dell-port-tracer-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: port_tracer_db
      POSTGRES_USER: porttracer_user
      POSTGRES_PASSWORD: porttracer_pass
    volumes:
      # Named volume for consistent database persistence
      - postgres_data_persistent:/var/lib/postgresql/data
      # Protected backups directory
      - ./backups:/backups
    networks:
      - dell-port-tracer
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U porttracer_user -d port_tracer_db']
      interval: 30s
      timeout: 10s
      retries: 5

  app:
    build:
      context: ./app
      dockerfile: Dockerfile
    container_name: dell-port-tracer-app
    restart: unless-stopped
    env_file:
      # Use single environment file
      - .env
    volumes:
      # Application logs (persistent)
      - ./logs/app:/app/logs
      # Protected backups directory
      - ./backups:/app/backups
      # Protected data directory (read-only)
      - ./data:/app/data:ro
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - dell-port-tracer
    healthcheck:
      test: ['CMD', 'curl', '-f', 'http://localhost:5000/health']
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    container_name: dell-port-tracer-nginx
    restart: unless-stopped
    ports:
      - '80:80'
      - '443:443'
    volumes:
      # Nginx configuration
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      # SSL certificates (auto-generated)
      - ./data/ssl:/etc/nginx/ssl:ro
      # Nginx logs
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - app
    networks:
      - dell-port-tracer
    healthcheck:
      test: ['CMD', 'nginx', '-t']
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  dell-port-tracer:
    driver: bridge

volumes:
  # Named volume with consistent name for database persistence
  # This survives container rebuilds and prevents data loss
  postgres_data_persistent:
    driver: local
    name: dell_port_tracer_postgres_data
```

### nginx Configuration

```nginx
# /etc/nginx/sites-available/dell-port-tracer
server {
    listen 443 ssl http2;
    server_name your-server.domain.com;

    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://localhost:5000/health;
        access_log off;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-server.domain.com;
    return 301 https://$server_name$request_uri;
}
```

## Environment Configuration

### Production Environment Variables

```bash
# .env file
# Database Configuration
DATABASE_URL=postgresql://dell_tracer_user:dell_tracer_pass@postgres:5432/dell_port_tracer
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=dell_port_tracer
POSTGRES_USER=dell_tracer_user
POSTGRES_PASSWORD=dell_tracer_pass

# Windows Authentication
WINDOWS_AUTH_ENABLED=true
LDAP_SERVER=your-domain-controller.com
LDAP_PORT=389
LDAP_USE_SSL=false
LDAP_BIND_DN=CN=service-account,OU=Service Accounts,DC=domain,DC=com
LDAP_BIND_PASSWORD=service-account-password
LDAP_USER_SEARCH_BASE=OU=Users,DC=domain,DC=com
LDAP_USER_SEARCH_FILTER=(sAMAccountName={username})
LDAP_GROUP_SEARCH_BASE=OU=Groups,DC=domain,DC=com

# Application Configuration
FLASK_ENV=production
SECRET_KEY=your-secret-key-here
SESSION_TIMEOUT=3600

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## Production Deployment Process (v2.1.3)

### 1. Server Preparation

```bash
# Install Docker and Docker Compose
sudo apt update
sudo apt install docker.io docker-compose-plugin curl git
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker  # Apply group membership

# Verify Docker installation
docker --version
docker-compose --version
```

### 2. Application Deployment (Recommended: Safe Script)

```bash
# Clone repository
git clone https://github.com/Crispy-Pasta/SwitchPortManager.git
cd SwitchPortManager

# Configure environment from template
cp config/.env.template .env

# Edit .env with your production configuration
vim .env  # Configure all required variables

# Deploy using safe script (automated with backup/rollback)
./deploy-safe.sh
```

### 3. Manual Deployment (Alternative)

```bash
# If you prefer manual control:

# Build application container
docker-compose -f docker-compose.prod.yml build --no-cache

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to initialize
sleep 30

# Verify deployment
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker logs dell-port-tracer-app --tail 10
curl -k https://localhost/health
```

### 4. SSL Certificate Management

**Production SSL certificates:**
```bash
# Create SSL directory
mkdir -p data/ssl

# For production CA certificates:
cp your-cert.pem data/ssl/fullchain.pem
cp your-key.pem data/ssl/privkey.pem
chmod 600 data/ssl/privkey.pem

# Update nginx configuration to use production certificates
# Then restart nginx container
docker restart dell-port-tracer-nginx
```

**Self-signed certificates (default):**
```bash
# SSL certificates are automatically generated on first run
# No additional configuration required
```

### 5. Database Operations

```bash
# Database is automatically initialized
# Manual operations if needed:

# Create manual database backup
docker exec dell-port-tracer-postgres pg_dump -U porttracer_user port_tracer_db > backup.sql

# Restore from backup
cat backup.sql | docker exec -i dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db

# Check database status
docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c "SELECT version();"
```

### 6. Active Directory Integration Testing

```bash
# Test Windows AD authentication (if configured)
docker exec dell-port-tracer-app python -c "from app.auth import test_ldap; test_ldap()"

# Check environment variables
docker exec dell-port-tracer-app printenv | grep -E 'AD_SERVER|LDAP|AUTH'

# Test application authentication
curl -k -X POST https://localhost/login -d "username=testuser&password=testpass"
```

### 7. Production Verification

```bash
# Complete production readiness check
echo "=== Container Status ==="
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

echo "=== Health Checks ==="
curl -k https://localhost/health | jq .

echo "=== SSL Certificate Info ==="
openssl s_client -connect localhost:443 -servername localhost < /dev/null 2>/dev/null | openssl x509 -noout -dates

echo "=== Database Connectivity ==="
docker exec dell-port-tracer-postgres pg_isready -U porttracer_user -d port_tracer_db

echo "=== Log Status ==="
ls -la logs/
docker logs dell-port-tracer-app --tail 5
docker logs dell-port-tracer-nginx --tail 5
```

## Monitoring and Maintenance

- **Health Checks**:
  - Use Docker health checks to monitor container status.
  - Configure external monitoring tools to ensure service availability.

- **Logs and Auditing**:
  - Implement logging for application and database containers.
  - Use centralized logging solutions for audit trails.

- **Backup and Recovery**:
  - Schedule regular database backups.
  - Ensure data snapshots and rollback strategies are in place.

## Security Considerations

- **Network Security**:
  - Enforce firewall rules and security groups to restrict network access.
  - Use encryption for data transmission securely (e.g. HTTPS).

- **Environment Security**:
  - Secure all environment files (.env) containing sensitive information.
  - Rotate keys, passwords, and secrets regularly.

- **User Access**:
  - Use principle of least privilege for user roles and access.
  - Ensure user accounts and permissions are audited regularly.

## Troubleshooting Server Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Application Downtime** | App unreachable, no response | Check Docker containers and logs |
| **Database Connection Failure** | Auth errors, connection refused | Verify DB config and restart container |
| **SSL Certificate Error** | Browser SSL warnings | Renew SSL/TLS certificate |

## Server Team Responsibilities

- **Deployment and Updates**:
  - Manage Docker deployment lifecycle.
  - Regularly update containers and dependencies.

- **Monitoring and Health Checks**:
  - Continuously monitor container health and performance.
  - Visualize and diagnose endpoint connectivity and problems.

- **Coordination and Support**:
  - Collaborate with network and development teams for integrated deliverables.
  - Assist in security audits and comprehensive testing.
