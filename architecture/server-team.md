# Dell Port Tracer - Server Team Architecture

## 🖥️ Server Team Overview

This documentation provides an overview of the server and infrastructure-related aspects of the Dell Port Tracer application, including deployment architecture, server components, monitoring, maintenance, and security.

## Server Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      SERVER ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────┘

                  User Workstation
                  ┌──────────────┐
                  │              │
                  │  Web Browser │
                  │              │
                  └───────┬──────┘
                          │
           HTTPS (Port 443) │
                          │
                          ▼
                  ┌──────────────┐
                  │   Internet    │
                  └──────────────┘
                          │
                          ▼
                ┌─────────────────┐
                │    Firewall     ◄───────────────────────────── User Authentication
                └─────────────────┘          Windows Active Directory (LDAP)
                          │
                          ▼
                ┌─────────────────┐
                │                 │
                │  nginx Reverse  │
                │     Proxy       │
                │                 │
                └─────────┬───────┘
                          │
                          ▼
          ┌────────────────────────────┐
          │        Docker Host         │
          └─────────────────┬──────────┘
                            │
                            │
    ┌────────────────────────────────────────────┐
    │                                            │
    │               Docker Network               │
    │                                            │
    ├────────────────────────────────────────────┤
    │   Docker Container: Flask App              │
    │   (Port 5000)                              │
    │--------------------------------------------│
    │   Docker Container: PostgreSQL Database    │
    │   (Port 5432)                              │
    │--------------------------------------------│
    │   Docker Container: Internal Services      │
    │                                            │
    └────────────────────────────────────────────┘
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

### Docker Compose Services

```yaml
# docker-compose.yml
version: '3.8'
services:
  port-tracer:
    image: dell-port-tracer:latest
    container_name: port-tracer
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://dell_tracer_user:dell_tracer_pass@postgres:5432/dell_port_tracer
      - WINDOWS_AUTH_ENABLED=true
      - LDAP_SERVER=your-domain-controller.com
      - LDAP_PORT=389
    depends_on:
      - postgres
    networks:
      - port-tracer-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15
    container_name: postgres
    environment:
      - POSTGRES_DB=dell_port_tracer
      - POSTGRES_USER=dell_tracer_user
      - POSTGRES_PASSWORD=dell_tracer_pass
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    ports:
      - "5432:5432"
    networks:
      - port-tracer-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U dell_tracer_user"]
      interval: 30s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:

networks:
  port-tracer-network:
    driver: bridge
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

## Deployment Steps

### 1. Server Preparation

```bash
# Install Docker and Docker Compose
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER

# Install nginx
sudo apt install nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 2. Application Deployment

```bash
# Clone repository
git clone https://github.com/your-org/dell-port-tracer.git
cd dell-port-tracer

# Configure environment
cp .env.example .env
# Edit .env with your configuration

# Build and start containers
docker-compose build
docker-compose up -d

# Verify deployment
docker-compose ps
docker-compose logs
```

### 3. nginx Configuration

```bash
# Copy nginx configuration
sudo cp nginx/dell-port-tracer.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/dell-port-tracer.conf /etc/nginx/sites-enabled/

# Test and reload nginx
sudo nginx -t
sudo systemctl reload nginx
```

### 4. SSL/TLS Certificate Setup

```bash
# Using Let's Encrypt (recommended)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-server.domain.com

# Or copy existing certificates
sudo cp your-certificate.crt /etc/ssl/certs/
sudo cp your-private.key /etc/ssl/private/
sudo chmod 600 /etc/ssl/private/your-private.key
```

### 5. Database Initialization

```bash
# Initialize database schema
docker-compose exec port-tracer python init_db.py

# Migrate data from SQLite (if applicable)
docker-compose exec port-tracer python migrate_data.py
```

### 6. Active Directory Integration Testing

```bash
# Test LDAP connectivity
docker-compose exec port-tracer python tools/test_ldap_connection.py

# Test user authentication
docker-compose exec port-tracer python tools/test_ad_auth.py
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
