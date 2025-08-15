# Dell Switch Port Tracer v2.1.3 - Production Deployment Guide

This guide explains how to deploy the Dell Switch Port Tracer application using Docker Compose for production environments with SSL/HTTPS, database persistence, and automated deployment.

## 📋 Prerequisites

### Required Software
- **Docker** (version 20.10 or later)
- **Docker Compose** (version 2.0 or later)
- **Git** (for cloning repository)
- **Linux server** (Ubuntu/CentOS/RHEL recommended)

### Server Requirements
- **CPU**: 2+ cores
- **RAM**: 4GB+ recommended 
- **Storage**: 20GB+ available space
- **Network**: SSH access to Dell switches
- **Ports**: 80, 443 available for HTTP/HTTPS

## 🏗️ Production Architecture

The application uses a 3-container Docker Compose setup:

- **dell-port-tracer-app**: Flask application server (Python)
- **dell-port-tracer-nginx**: Reverse proxy with SSL/HTTPS termination
- **dell-port-tracer-postgres**: Database with persistent storage

### Key Features
- ✅ **SSL/HTTPS enabled** with self-signed certificates
- ✅ **Database persistence** using named Docker volumes
- ✅ **Automatic backups** for configuration and database
- ✅ **Health monitoring** for all services
- ✅ **Safe deployment** with rollback capability

## 🚀 Quick Start (Recommended)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/Crispy-Pasta/SwitchPortManager.git
cd SwitchPortManager

# Copy environment template
cp config/.env.template .env
```

### 2. Configure Environment

Edit `.env` file with your settings:
```env
# Required: Application security
SECRET_KEY=your_secure_secret_key_here

# Required: Dell switch credentials
SWITCH_USERNAME=your_switch_username
SWITCH_PASSWORD=your_switch_password

# Required: User passwords
ADMIN_PASSWORD=your_admin_password
OSS_PASSWORD=your_oss_password
NETADMIN_PASSWORD=your_netadmin_password
SUPERADMIN_PASSWORD=your_superadmin_password

# Optional: Active Directory
USE_WINDOWS_AUTH=true
AD_SERVER=10.20.100.15
AD_DOMAIN=your-domain.com
AD_BASE_DN=DC=your-domain,DC=com
```

### 3. Deploy with Safe Script

```bash
# Automated deployment with backup protection
./deploy-safe.sh
```

### 4. Access the Application

After deployment:
- **HTTPS**: `https://your-server-ip/`
- **HTTP**: `http://your-server-ip/`
- **Custom domain**: Configure DNS for your domain

## 📝 Manual Deployment Steps

**If you prefer manual control over the automated deploy-safe.sh script:**

### Step 1: Clone and Prepare

```bash
# Clone repository
git clone https://github.com/Crispy-Pasta/SwitchPortManager.git
cd SwitchPortManager

# Create environment file
cp config/.env.template .env
```

### Step 2: Configure Environment Variables

Edit `.env` with your specific values:
```bash
vim .env  # or nano, gedit, etc.
```

Required configuration:
```env
# Application Security (generate secure key)
SECRET_KEY=$(openssl rand -hex 32)

# Dell Switch Credentials
SWITCH_USERNAME=your_switch_admin_user
SWITCH_PASSWORD=your_secure_switch_password

# Database (auto-configured for Docker)
DATABASE_URL=postgresql://porttracer_user:porttracer_pass@postgres:5432/port_tracer_db

# Application User Passwords
ADMIN_PASSWORD=your_secure_admin_password
OSS_PASSWORD=your_oss_password
NETADMIN_PASSWORD=your_netadmin_password
SUPERADMIN_PASSWORD=your_superadmin_password

# Active Directory (if used)
USE_WINDOWS_AUTH=true
AD_SERVER=your_ad_server_ip
AD_DOMAIN=your.domain.com
AD_BASE_DN=DC=your,DC=domain,DC=com
```

### Step 3: Build and Deploy

```bash
# Build application container
docker-compose -f docker-compose.prod.yml build --no-cache

# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to initialize
sleep 30
```

### Step 4: Verify Deployment

```bash
# Check all containers are running
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# Check logs
docker logs dell-port-tracer-app --tail 20
docker logs dell-port-tracer-nginx --tail 10
docker logs dell-port-tracer-postgres --tail 10

# Test application health
curl -k https://localhost/health
```

### Step 5: Configure SSL (Optional)

**For production SSL certificates:**
```bash
# Place your SSL certificates in data/ssl/
mkdir -p data/ssl
cp your-cert.pem data/ssl/fullchain.pem
cp your-key.pem data/ssl/privkey.pem

# Update nginx.conf to use your certificates
# Then restart nginx
docker restart dell-port-tracer-nginx
```

## 🔧 Configuration

### Complete Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | Flask application secret key | - | Yes |
| `FLASK_ENV` | Application environment | `production` | No |
| `DATABASE_URL` | PostgreSQL connection string | Auto-configured | No |
| `SWITCH_USERNAME` | SSH username for switches | - | Yes |
| `SWITCH_PASSWORD` | SSH password for switches | - | Yes |
| `ADMIN_PASSWORD` | Admin user password | - | Yes |
| `OSS_PASSWORD` | OSS user password | - | Yes |
| `NETADMIN_PASSWORD` | NetAdmin user password | - | Yes |
| `SUPERADMIN_PASSWORD` | SuperAdmin user password | - | Yes |
| `USE_WINDOWS_AUTH` | Enable Windows/AD authentication | `false` | No |
| `AD_SERVER` | Active Directory server IP | - | No |
| `AD_DOMAIN` | Active Directory domain | - | No |
| `AD_BASE_DN` | Active Directory base DN | - | No |
| `SYSLOG_ENABLED` | Enable syslog logging | `true` | No |
| `SYSLOG_SERVER` | Syslog server IP | - | No |

### Docker Resource Limits

**Application Container:**
- CPU: 1.0 cores
- Memory: 1GB
- Restart: unless-stopped

**Database Container:**
- CPU: 0.5 cores  
- Memory: 512MB
- Restart: unless-stopped

**Nginx Container:**
- CPU: 0.25 cores
- Memory: 128MB
- Restart: unless-stopped

### Persistent Storage

- **Named Volume**: `dell_port_tracer_postgres_data` (database persistence)
- **Bind Mounts**: 
  - `./logs/nginx:/var/log/nginx` (nginx logs)
  - `./logs/app:/app/logs` (application logs)
  - `./backups:/app/backups` (database backups)

## 🔒 Security Features

### Container Security
- **Non-root execution**: All containers run as non-privileged users
- **Network isolation**: Docker network bridges provide container isolation
- **Resource limits**: CPU and memory limits prevent resource exhaustion
- **Read-only containers**: Critical system files are read-only where possible

### SSL/HTTPS Security
- **Automatic SSL**: Self-signed certificates generated on first run
- **HTTPS redirect**: HTTP traffic automatically redirected to HTTPS
- **TLS protocols**: Support for TLS 1.2 and 1.3
- **Security headers**: X-Frame-Options, X-Content-Type-Options, XSS-Protection

### Application Security
- **Environment-based secrets**: Sensitive data stored in .env file
- **Session management**: Secure session handling with configurable timeouts
- **AD integration**: Optional LDAP authentication with role-based access
- **Audit logging**: Complete activity tracking for compliance

## 📈 Monitoring and Health Checks

### Built-in Health Checks
- **Application health**: `/health` endpoint provides JSON status
- **Database connectivity**: Automatic PostgreSQL connection testing
- **Container health**: Docker health checks for all services

### Monitoring Commands

```bash
# Check all containers status
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# View application logs
docker logs dell-port-tracer-app --follow

# Check nginx access logs
docker logs dell-port-tracer-nginx --tail 50

# Monitor database
docker logs dell-port-tracer-postgres --tail 20

# Test application health
curl -k https://localhost/health
```

### Log Locations
- **Application logs**: `./logs/app/`
- **Nginx logs**: `./logs/nginx/`  
- **Database backups**: `./backups/`

## 🔄 Maintenance Operations

### Update Application Code

```bash
# Pull latest code changes
git pull origin main

# Safe deployment with automatic backup
./deploy-safe.sh
```

### Update Environment Configuration

```bash
# Edit environment variables
vim .env

# Restart application to pick up changes
docker-compose -f docker-compose.prod.yml restart app
```

### Database Operations

```bash
# Create manual database backup
docker exec dell-port-tracer-postgres pg_dump -U porttracer_user port_tracer_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
cat backup_file.sql | docker exec -i dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db

# View database size
docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c "SELECT pg_size_pretty(pg_database_size('port_tracer_db'));"
```

### SSL Certificate Updates

```bash
# Replace with production certificates
cp your-cert.pem data/ssl/fullchain.pem
cp your-key.pem data/ssl/privkey.pem

# Restart nginx to load new certificates
docker restart dell-port-tracer-nginx
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Containers Not Starting
```bash
# Check container status
docker ps -a

# Check specific container logs
docker logs dell-port-tracer-app --tail 50

# Check Docker Compose status
docker-compose -f docker-compose.prod.yml ps
```

#### 2. Database Connection Issues
```bash
# Test database connectivity
docker exec dell-port-tracer-postgres psql -U porttracer_user -d port_tracer_db -c "SELECT version();"

# Check database logs
docker logs dell-port-tracer-postgres --tail 30

# Verify database volume
docker volume inspect dell_port_tracer_postgres_data
```

#### 3. SSL/HTTPS Issues
```bash
# Check nginx configuration
docker exec dell-port-tracer-nginx nginx -t

# Check SSL certificates
docker exec dell-port-tracer-nginx ls -la /etc/ssl/certs/ssl-cert-snakeoil.pem

# Test HTTPS connectivity
curl -k -I https://localhost/
```

#### 4. Application Access Issues
```bash
# Check port bindings
docker port dell-port-tracer-nginx

# Test application endpoint
curl -k https://localhost/health

# Check environment variables
docker exec dell-port-tracer-app printenv | grep -E 'DATABASE_URL|SWITCH_USERNAME'
```

### Useful Maintenance Commands

```bash
# View all application resources
docker-compose -f docker-compose.prod.yml ps
docker volume ls | grep dell
docker network ls | grep dell

# Complete cleanup (DANGER: loses data)
docker-compose -f docker-compose.prod.yml down -v
docker system prune -a

# Safe restart of all services
docker-compose -f docker-compose.prod.yml restart

# Access container shells
docker exec -it dell-port-tracer-app bash
docker exec -it dell-port-tracer-postgres psql -U porttracer_user port_tracer_db
```

## 🌐 Production Access Options

### Direct Server Access
- **HTTPS**: `https://server-ip-address/`
- **HTTP**: `http://server-ip-address/` (redirects to HTTPS)

### Custom Domain Setup
1. **Configure DNS**: Point your domain to the server IP
2. **Update nginx.conf**: Add your domain to server_name directive
3. **SSL certificates**: Replace self-signed certs with CA-signed certificates
4. **Restart nginx**: `docker restart dell-port-tracer-nginx`

### Load Balancer Integration
- Configure your load balancer to forward to ports 80/443
- Use health check endpoint: `/health`
- Enable session affinity for login consistency

## 📈 Production Best Practices

### Security Hardening
- Replace default passwords in .env file
- Use strong, unique SECRET_KEY
- Implement proper SSL certificates from trusted CA
- Regular security updates: `docker-compose pull && ./deploy-safe.sh`
- Monitor access logs for suspicious activity

### Performance Optimization
- Monitor resource usage: `docker stats`
- Adjust container resource limits as needed
- Regular database maintenance and backups
- Log rotation to prevent disk space issues

### High Availability
- Deploy on multiple servers with load balancer
- Use external PostgreSQL for database clustering
- Implement monitoring with Prometheus/Grafana
- Set up automated backups to external storage

### Backup Strategy
- **Automated daily backups** via deploy-safe.sh
- **Configuration backup**: .env, nginx.conf, docker-compose.prod.yml
- **Database backups**: Automated PostgreSQL dumps
- **SSL certificates**: Backup custom certificates
- **Switch inventory**: Backup switches.json regularly

## 📞 Support

### Troubleshooting Steps
1. **Check container status**: `docker ps`
2. **Review application logs**: `docker logs dell-port-tracer-app --tail 50`
3. **Test connectivity**: `curl -k https://localhost/health`
4. **Consult documentation**: See `docs/PRODUCTION_TROUBLESHOOTING.md`
5. **Safe restart**: `./deploy-safe.sh`

### Documentation Resources
- **Main README**: Complete feature documentation
- **Production Troubleshooting**: `docs/PRODUCTION_TROUBLESHOOTING.md`
- **User Guide**: `docs/USER_GUIDE.md`
- **DevOps Guide**: `docs/DEVOPS_GUIDE.md`

---

**Deployment Guide v2.1.3**  
**Last Updated**: August 2025  
**Production Ready**: ✅ Verified and Tested
