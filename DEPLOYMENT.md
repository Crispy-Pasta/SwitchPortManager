# Dell Port Tracer Deployment Guide

## 🚀 Safe Deployment Process

This document explains how to safely deploy Dell Port Tracer updates without losing configuration or database data.

## 📋 Prerequisites

- Docker and Docker Compose installed
- SSH access to production server
- Backup of current configuration

## 🏗️ Repository Structure

```
DellPortTracer/
├── docker-compose.yml          # Development configuration
├── docker-compose.prod.yml     # Production configuration  
├── deploy-safe.sh              # Safe deployment script
├── .env.example               # Environment template
├── config/                    # Configuration examples
│   ├── .env.example
│   ├── .env.syslog.example
│   └── .env.test
└── scripts/                   # Legacy scripts (deprecated)
    ├── deploy-production.sh   # OLD - Do not use
    └── deploy.sh             # OLD - Do not use
```

## 🎯 Production Server Structure

```
/opt/dell-port-tracer/
├── app/                       # Application code (replaceable)
├── data/                      # 🔒 PROTECTED DATA (never replace)
│   ├── .env.production        # Switch credentials & settings
│   ├── switches.json          # Switch inventory
│   └── ssl/                   # SSL certificates
├── backups/                   # Automatic backups
│   └── deployment_YYYYMMDD_HHMMSS/  # Timestamped backups
├── logs/                      # Application and deployment logs
├── docker-compose.prod.yml    # Production Docker configuration
├── nginx.conf                 # Nginx configuration
└── deploy-safe.sh            # Safe deployment script
```

## 🛠️ Deployment Process

### Step 1: Repository Updates
Update these files in your repository when making changes:

1. **docker-compose.yml** - Development configuration
2. **docker-compose.prod.yml** - Production configuration  
3. **deploy-safe.sh** - Deployment script
4. **.env.example** - Environment template

### Step 2: Safe Production Deployment

```bash
# SSH to production server
ssh user@production-server

# Navigate to deployment directory
cd /opt/dell-port-tracer

# Run safe deployment
./deploy-safe.sh
```

The safe deployment script will:
1. ✅ Create automatic backup of all critical files
2. ✅ Protect configuration files from being overwritten
3. ✅ Use consistent database volumes (no data loss)
4. ✅ Validate deployment configuration
5. ✅ Deploy using Docker Compose only
6. ✅ Perform health checks
7. ✅ Provide deployment summary

## 🔒 Data Protection Features

### Protected Files (Never Overwritten)
- `/opt/dell-port-tracer/data/.env.production` - Switch credentials
- `/opt/dell-port-tracer/data/switches.json` - Switch inventory  
- `/opt/dell-port-tracer/data/ssl/` - SSL certificates

### Persistent Database
- **Volume name**: `dell_port_tracer_postgres_data`
- **Consistent across deployments**: No data loss
- **Automatic backups**: Created before each deployment

### Automatic Backups
- **Location**: `/opt/dell-port-tracer/backups/deployment_YYYYMMDD_HHMMSS/`
- **Contents**: Environment files, database dump, Docker Compose config
- **Retention**: Manual cleanup (consider automation)

## ⚠️ Migration from Old Deployment Method

If you're currently using the old deployment scripts:

### 1. Check Current Volumes
```bash
docker volume ls | grep postgres
```

### 2. Backup Current Data
```bash
# Backup database
docker exec <postgres_container> pg_dump -U <user> <database> > backup.sql

# Backup environment files
cp .env /opt/dell-port-tracer/data/.env.production
```

### 3. Migrate to New Structure
```bash
# Create protected data directory
mkdir -p /opt/dell-port-tracer/data

# Move critical files to protected location
mv .env /opt/dell-port-tracer/data/.env.production
mv switches.json /opt/dell-port-tracer/data/switches.json
mv ssl /opt/dell-port-tracer/data/ssl

# Set proper permissions
chmod 600 /opt/dell-port-tracer/data/.env.production
chmod -R 600 /opt/dell-port-tracer/data/ssl
```

### 4. Update Docker Compose
Replace old Docker Compose configuration with the new production version that uses protected data paths.

## 🔧 Troubleshooting

### Multiple Database Volumes
If you see multiple postgres volumes:
```bash
docker volume ls | grep postgres
```

The deployment script will warn you about this and help consolidate to the consistent named volume.

### Environment Variables Not Loading
Check if the protected environment file exists:
```bash
ls -la /opt/dell-port-tracer/data/.env.production
```

### Service Health Check Failures
Check the deployment logs:
```bash
tail -f /opt/dell-port-tracer/logs/deployment.log
```

### Rollback Procedure
1. Find the last successful backup:
```bash
cat /opt/dell-port-tracer/.last_backup
```

2. Restore from backup:
```bash
backup_path=$(cat /opt/dell-port-tracer/.last_backup)
cp $backup_path/.env.production /opt/dell-port-tracer/data/
cp $backup_path/docker-compose.prod.yml /opt/dell-port-tracer/
```

3. Restart services:
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

## 📝 Best Practices

### Do ✅
- Always use `./deploy-safe.sh` for production deployments
- Keep the `/opt/dell-port-tracer/data/` directory protected
- Test deployment process in staging environment first
- Monitor deployment logs during deployment
- Verify services are healthy after deployment

### Don't ❌
- Don't use old `docker run` deployment scripts
- Don't manually edit files in `/opt/dell-port-tracer/data/`
- Don't use `docker-compose down -v` (destroys volumes)
- Don't skip backups before deployment
- Don't deploy directly to production without testing

## 🆘 Emergency Procedures

### Complete System Recovery
If everything breaks:

1. **Stop all containers**:
```bash
docker-compose -f docker-compose.prod.yml down
```

2. **Restore from latest backup**:
```bash
backup_path=$(cat /opt/dell-port-tracer/.last_backup)
cp -r $backup_path/* /opt/dell-port-tracer/data/
```

3. **Restore database**:
```bash
docker-compose -f docker-compose.prod.yml up -d postgres
docker exec -i dell-port-tracer-postgres psql -U porttracer_user port_tracer_db < $backup_path/database_backup.sql
```

4. **Start all services**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## 📞 Support

For deployment issues:
1. Check `/opt/dell-port-tracer/logs/deployment.log`
2. Run `./deploy-safe.sh --help` for options
3. Verify all protected files exist in `/opt/dell-port-tracer/data/`
4. Contact system administrator if issues persist

---

**Remember**: The goal is **zero downtime, zero data loss** deployments. Always use the safe deployment process!
