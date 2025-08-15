# Dell Port Tracer Deployment Fix Plan

## 🚨 Current Issues Identified

### 1. Environment File Problems
- **OLD script**: Uses `/home/janzen/.env`
- **NEW compose**: Uses `/opt/dell-port-tracer/.env`
- **Result**: Configuration gets overwritten during deployments

### 2. Database Volume Confusion
- **Multiple volumes**: `app_postgres_data` vs `dell-port-tracer_postgres_data`
- **Different deployment methods** create different volumes
- **Result**: Database data lost between deployments

### 3. Conflicting Deployment Methods
- **Legacy script**: `docker run` with different config
- **New method**: `docker-compose` with different volumes
- **Result**: Inconsistent deployments and data loss

## 🛠️ Solutions

### Solution 1: Standardize on Docker Compose Only
- Remove the old `docker run` deployment script
- Use ONLY `docker-compose` for all deployments
- Ensure consistent volume naming and persistence

### Solution 2: Protect Configuration Files
- Move `.env` to protected location outside app directory
- Create template and production separation
- Add backup/restore procedures for critical configs

### Solution 3: Fix Database Persistence
- Consolidate to single named volume
- Add database backup/restore procedures
- Ensure volume survives container rebuilds

### Solution 4: Deployment Process Improvements
- Create deployment checklist
- Add pre-deployment backups
- Implement rollback procedures
- Add configuration drift detection

## 📋 Implementation Steps

1. **Backup current data**
2. **Create protected configuration structure**
3. **Update Docker Compose for persistence**
4. **Create new deployment script**
5. **Test deployment process**
6. **Document procedures**

## 📁 Recommended Directory Structure

```
/opt/dell-port-tracer/
├── app/                    # Application code (can be replaced)
├── data/                   # Protected data (NEVER replace)
│   ├── .env.production     # Protected environment file
│   ├── switches.json       # Protected switch inventory
│   └── ssl/                # SSL certificates
├── backups/                # Automated backups
├── logs/                   # Application logs
└── docker-compose.prod.yml # Docker configuration
```

## 🔒 Protection Rules

1. **NEVER overwrite** files in `/opt/dell-port-tracer/data/`
2. **ALWAYS backup** before deployment
3. **USE ONLY** Docker Compose for production
4. **VERIFY** database volume consistency
5. **TEST** deployment in staging first
