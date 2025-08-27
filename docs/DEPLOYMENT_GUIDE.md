# Dell Switch Port Tracer - First-Time Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Dell Switch Port Tracer application in a production environment. The application has been enhanced with automatic database initialization, improved security settings, streamlined deployment processes, and production-grade health checks.

**Version**: 2.1.6
**Target Environment**: Production/Staging  
**Prerequisites**: Docker, Docker Compose, PostgreSQL  

## 🚀 Quick Start Deployment

### 1. Prerequisites

Ensure your system meets the following requirements:

- **Docker**: Version 20.10+ 
- **Docker Compose**: Version 2.0+
- **System Resources**: 
  - RAM: 2GB minimum, 4GB recommended
  - Storage: 10GB minimum, 20GB recommended
  - CPU: 2 cores minimum

### 2. Download and Setup

```bash
# Clone the repository
git clone https://github.com/Crispy-Pasta/SwitchPortManager.git
cd SwitchPortManager

# Copy environment template
cp .env.example .env
```

### 3. Configure Environment Variables

Edit the `.env` file with your specific configuration:

```bash
# Required Database Configuration
POSTGRES_DB=port_tracer_db
POSTGRES_USER=dell_tracer_user
POSTGRES_PASSWORD=YOUR_SECURE_DATABASE_PASSWORD
DATABASE_URL=postgresql://dell_tracer_user:YOUR_SECURE_DATABASE_PASSWORD@postgres:5432/port_tracer_db

# Required Application Security
SECRET_KEY=YOUR_GENERATED_SECRET_KEY  # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SESSION_COOKIE_SECURE=false  # Set to 'true' for HTTPS in production

# Required Dell Switch SSH Credentials
SWITCH_USERNAME=your_switch_admin_username
SWITCH_PASSWORD=your_switch_admin_password

# Optional User Password Overrides (recommended for production)
WEB_PASSWORD=your_secure_admin_password
NETADMIN_PASSWORD=your_secure_netadmin_password
SUPERADMIN_PASSWORD=your_secure_superadmin_password
```

### 4. Deploy the Application

```bash
# Start the application stack
docker-compose up -d

# Monitor the startup process
docker-compose logs -f app

# Verify all services are running
docker-compose ps
```

### 5. Initial Access

The application will be available at:
- **HTTP**: http://your-server-ip:5000
- **Default Login**: 
  - Username: `admin`
  - Password: `password` (or your configured `WEB_PASSWORD`)

## 📋 Detailed Configuration Guide

### Environment Variables Reference

#### Database Configuration (Required)
```bash
POSTGRES_DB=port_tracer_db              # Database name
POSTGRES_USER=dell_tracer_user          # Database username  
POSTGRES_PASSWORD=secure_password_123   # Database password (CHANGE THIS)
POSTGRES_HOST=postgres                  # Database host (use 'postgres' for Docker Compose)
POSTGRES_PORT=5432                      # Database port
DATABASE_URL=postgresql://...           # Complete connection string (auto-constructed if not set)
```

#### Application Security (Required)
```bash
SECRET_KEY=random_secret_key_here       # Flask secret key - MUST be random and secure
FLASK_ENV=production                    # Flask environment mode
SESSION_COOKIE_SECURE=false            # Set to 'true' for HTTPS deployments
SESSION_COOKIE_HTTPONLY=true           # HTTP-only cookies for security
SESSION_COOKIE_SAMESITE=Lax            # SameSite cookie policy
PERMANENT_SESSION_LIFETIME=5            # Session timeout in minutes
```

#### Dell Switch Credentials (Required)
```bash
SWITCH_USERNAME=admin                   # SSH username for Dell switches
SWITCH_PASSWORD=switch_admin_password   # SSH password for Dell switches
```

#### Web Application Users (Optional)
```bash
# Override default passwords (highly recommended for production)
OSS_PASSWORD=oss123                     # OSS user password
NETADMIN_PASSWORD=netadmin123           # Network Admin password
SUPERADMIN_PASSWORD=superadmin123       # Super Admin password  
WEB_PASSWORD=password                   # Legacy admin user password
```

#### Performance Tuning (Optional)
```bash
CPU_GREEN_THRESHOLD=40                  # CPU monitoring green zone (%)
CPU_YELLOW_THRESHOLD=60                 # CPU monitoring yellow zone (%)
CPU_RED_THRESHOLD=80                    # CPU monitoring red zone (%)
MAX_CONCURRENT_SWITCHES=8               # Max concurrent switch connections
GLOBAL_MAX_CONCURRENT=64                # Global connection limit
```

### Docker Compose Profiles

The application supports different deployment profiles:

#### Development Profile (Default)
```bash
docker-compose up -d
```

#### Production Profile
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 🔧 Database Initialization

The application now includes **automatic database initialization** that runs on container startup:

### What Happens Automatically

1. **Connection Retry**: Waits for PostgreSQL to become ready (up to 60 seconds)
2. **Schema Creation**: Creates all required tables (`site`, `floor`, `switch`) 
3. **Structure Validation**: Verifies table structures and relationships
4. **Status Reporting**: Provides detailed logs of initialization progress

### Manual Database Operations

If you need to manually manage the database:

```bash
# Initialize database schema manually
docker-compose exec app python init_db.py

# Force recreate all tables (DANGEROUS - development only)
docker-compose exec app python init_db.py --force

# Check database status
docker-compose exec postgres psql -U dell_tracer_user -d port_tracer_db -c "\\dt"
```

## 🛠️ Troubleshooting Common Issues

### Issue: Database Connection Fails

**Symptoms**: Application logs show "connection refused" or "database not available"

**Solution**:
```bash
# Check if PostgreSQL container is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Restart the database service
docker-compose restart postgres

# Wait for database to be ready, then restart app
docker-compose restart app
```

### Issue: Session Login Loop

**Symptoms**: Login succeeds but immediately redirects back to login page

**Causes & Solutions**:

1. **HTTP vs HTTPS Cookie Issue**:
   ```bash
   # Set SESSION_COOKIE_SECURE=false in .env for HTTP deployments
   SESSION_COOKIE_SECURE=false
   ```

2. **Missing Secret Key**:
   ```bash
   # Generate a proper secret key
   python -c "import secrets; print(secrets.token_hex(32))"
   # Add to .env file as SECRET_KEY
   ```

### Issue: Switch Connection Failures

**Symptoms**: Port tracing or VLAN operations fail with "connection refused"

**Solution**:
```bash
# Verify switch credentials in .env
SWITCH_USERNAME=correct_username
SWITCH_PASSWORD=correct_password

# Test SSH connectivity manually
ssh username@switch-ip-address

# Check application logs for specific error messages
docker-compose logs app | grep -i switch
```

### Issue: Permission Denied in Container

**Symptoms**: Container fails to start with permission errors

**Solution**:
```bash
# Fix file permissions
sudo chown -R 1000:1000 ./logs ./backups

# Rebuild container with correct permissions
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## 🔒 Security Considerations

### Production Security Checklist

- [ ] **Change all default passwords** in `.env` file
- [ ] **Generate secure SECRET_KEY** using cryptographically secure methods
- [ ] **Set SESSION_COOKIE_SECURE=true** for HTTPS deployments
- [ ] **Use strong database credentials** (avoid default values)
- [ ] **Restrict network access** to application ports (5000, 5432)
- [ ] **Enable HTTPS** using reverse proxy (nginx, Traefik)
- [ ] **Regular security updates** of container images
- [ ] **Monitor audit logs** in `audit.log` file
- [ ] **Backup database regularly** using PostgreSQL tools

### Network Security

```bash
# Recommended firewall rules (adjust for your environment)
sudo ufw allow 80    # HTTP (if using reverse proxy)
sudo ufw allow 443   # HTTPS (if using reverse proxy)
sudo ufw deny 5000   # Direct app access (use reverse proxy instead)
sudo ufw deny 5432   # PostgreSQL (internal Docker network only)
```

## 📊 Monitoring and Maintenance

### Health Checks

The application includes built-in health monitoring:

```bash
# Check application health
curl http://localhost:5000/health

# Monitor container health
docker-compose ps

# View detailed health check logs
docker inspect --format='{{json .State.Health}}' container-name | jq
```

### Log Management

```bash
# Application logs
docker-compose logs app

# Database logs  
docker-compose logs postgres

# Audit logs (user actions)
docker-compose exec app tail -f audit.log

# System logs (errors, warnings)
docker-compose exec app tail -f port_tracer.log
```

### Database Backup

```bash
# Create database backup
docker-compose exec postgres pg_dump -U dell_tracer_user port_tracer_db > backup-$(date +%Y%m%d-%H%M%S).sql

# Restore database backup
docker-compose exec -T postgres psql -U dell_tracer_user port_tracer_db < backup-file.sql
```

## 🔄 Upgrade Procedures

### Minor Version Updates

```bash
# Pull latest images
docker-compose pull

# Restart with new images
docker-compose up -d

# Monitor upgrade logs
docker-compose logs -f app
```

### Major Version Updates

```bash
# Backup database before upgrading
docker-compose exec postgres pg_dump -U dell_tracer_user port_tracer_db > pre-upgrade-backup.sql

# Stop services
docker-compose down

# Pull new version
git pull origin main

# Update environment if needed
cp .env.example .env.new
# Merge your settings into .env.new, then replace .env

# Start with new version
docker-compose up -d

# Verify functionality
curl http://localhost:5000/health
```

## 🆘 Emergency Procedures

### Complete System Reset (Development Only)

⚠️ **WARNING**: This will destroy all data!

```bash
# Stop all services
docker-compose down

# Remove all volumes (DESTRUCTIVE)
docker-compose down -v

# Remove all images
docker-compose down --rmi all

# Clean rebuild
docker-compose build --no-cache
docker-compose up -d
```

### Rollback to Previous Version

```bash
# Stop current version
docker-compose down

# Checkout previous version
git checkout HEAD~1

# Restore database backup if needed
docker-compose up -d postgres
docker-compose exec -T postgres psql -U dell_tracer_user port_tracer_db < backup-file.sql

# Start previous version
docker-compose up -d
```

## 📞 Support and Resources

### Documentation
- **API Documentation**: `/docs/API.md`
- **Architecture Guide**: `/architecture/README.md`
- **VLAN Management**: `/docs/VLAN_MANAGEMENT_TECHNICAL.md`

### Logs and Troubleshooting
- **Application Logs**: `docker-compose logs app`
- **Audit Logs**: Container `/app/audit.log`
- **Health Endpoint**: `http://localhost:5000/health`

### Community and Support
- **Repository**: https://github.com/Crispy-Pasta/SwitchPortManager
- **Issues**: Create GitHub issues for bugs and feature requests
- **Documentation**: Keep this guide updated with your environment specifics

---

**Last Updated**: August 2025  
**Version**: 2.1.6  
**Maintainer**: Network Operations Team
