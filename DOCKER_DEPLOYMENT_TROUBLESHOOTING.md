# Docker Deployment Troubleshooting Guide

## Common Deployment Issues and Solutions

### Issue 1: Missing Directories During Docker Build

**Symptom:**
```
COPY failed: file not found in build context or excluded by .dockerignore: stat tools/: file does not exist
```

**Root Cause:**
The Dockerfile references directories (`tools/`, `docs/`) that may not exist in all deployment environments.

**Solutions:**

1. **Option A: Remove missing directories from Dockerfile**
   ```bash
   # Edit Dockerfile and remove these lines if directories don't exist:
   # COPY --chown=app:app tools/ ./tools/
   # COPY --chown=app:app docs/ ./docs/
   ```

2. **Option B: Create empty directories**
   ```bash
   mkdir -p tools docs
   touch tools/.gitkeep docs/.gitkeep
   ```

3. **Option C: Use .dockerignore (if you want to exclude them)**
   ```bash
   echo "tools/" >> .dockerignore
   echo "docs/" >> .dockerignore
   ```

### Issue 2: Database Initialization Failures

**Symptom:**
```
python: can't open file '/app/init_db.py': [Errno 2] No such file or directory
❌ Database initialization failed
```

**Root Cause:**
The docker-entrypoint.sh script expects database initialization files that may not exist or may already be initialized.

**Solutions:**

The updated entrypoint script now handles this gracefully by:
- Checking if initialization files exist before running them
- Continuing execution even if initialization fails (database might already be set up)
- Providing informative log messages about what's happening

**Manual Fix for Production:**
If you encounter this issue, edit the entrypoint script to skip database initialization:
```bash
# Comment out or remove these lines in docker-entrypoint.sh:
# if python init_db.py; then
#     log "✅ Database initialization completed successfully"
# else
#     log "❌ Database initialization failed"
#     exit 1
# fi
```

### Issue 3: Container Name Conflicts

**Symptom:**
```
ERROR: for app  Cannot create container for service app: Conflict. The container name "/dell-port-tracer-app" is already in use
```

**Solution:**
```bash
# Remove the existing container
docker container rm -f dell-port-tracer-app
# Or use docker-compose to clean up
docker-compose down
docker-compose up -d
```

### Issue 4: Container Restart Loops

**Symptom:**
Container keeps restarting and shows "Restarting" status in `docker-compose ps`.

**Debugging Steps:**
1. Check the logs:
   ```bash
   docker-compose logs --tail=50 app
   ```

2. Check if the application files exist in the container:
   ```bash
   docker exec -it dell-port-tracer-app ls -la /app/
   ```

3. Check the entrypoint script permissions:
   ```bash
   docker exec -it dell-port-tracer-app ls -la /app/docker-entrypoint.sh
   ```

**Common Causes:**
- Missing application files (wsgi.py or run.py)
- Database initialization failures causing exit
- Port conflicts
- Insufficient permissions

## Best Practices for Production Deployment

### 1. Pre-deployment Checklist

- [ ] Verify all required files exist in the repository
- [ ] Test Docker build locally before deploying
- [ ] Backup production database before updating
- [ ] Check that the database container is healthy
- [ ] Verify network connectivity between containers

### 2. Safe Deployment Process

1. **Stop only the app container** (preserve database and nginx):
   ```bash
   docker-compose stop app
   ```

2. **Backup database** (if needed):
   ```bash
   docker exec dell-port-tracer-postgres pg_dump -U dell_tracer_user port_tracer_db > backup.sql
   ```

3. **Build new image**:
   ```bash
   docker-compose build --no-cache app
   ```

4. **Remove old container and start new one**:
   ```bash
   docker-compose rm -f app
   docker-compose up -d app
   ```

5. **Monitor startup**:
   ```bash
   docker-compose logs -f app
   ```

### 3. Rollback Strategy

If deployment fails:
```bash
# Stop the failing container
docker-compose stop app

# Revert to previous image (if tagged)
docker tag dell-port-tracer-app:previous dell-port-tracer-app:latest

# Restart with previous version
docker-compose up -d app
```

## Environment-Specific Considerations

### Development Environment
- May have different directory structures
- Database initialization might be needed
- Use `ENVIRONMENT=development` for Flask dev server

### Production Environment
- Database should already be initialized
- May have customized configuration files
- Always use Gunicorn in production
- Ensure proper backup procedures

## Monitoring and Health Checks

### Check Container Health
```bash
# Check all containers
docker-compose ps

# Check specific container health
docker inspect dell-port-tracer-app | grep Health -A 10

# Manual health check
curl -f http://localhost:5000/health
```

### Log Monitoring
```bash
# Follow real-time logs
docker-compose logs -f app

# Check specific time range
docker-compose logs --since="1h" app

# Check for errors
docker-compose logs app | grep -i error
```

## Contact and Support

If you encounter issues not covered in this guide:

1. Check the application logs first
2. Verify Docker and docker-compose versions
3. Check system resources (disk space, memory)
4. Review any custom configurations

---

**Last Updated:** $(date)
**Version:** 2.1.8
