# Production Deployment Troubleshooting Guide

This document covers common issues encountered during production deployment and their solutions.

## 🚨 Common Issues & Solutions

### Issue 1: Nginx 502 Bad Gateway Error

**Problem:** Nginx returns 502 Bad Gateway when accessing the application.

**Root Cause:** Nginx configuration pointing to wrong backend port.

**Solution:**
1. Check nginx configuration:
   ```bash
   cat /etc/nginx/sites-enabled/kmc-port-tracer.conf
   ```

2. Update proxy_pass to correct port:
   ```bash
   sudo sed -i 's/8443/5000/g' /etc/nginx/sites-enabled/kmc-port-tracer.conf
   sudo nginx -t
   sudo nginx -s reload
   ```

**Prevention:** Use the provided `fix-nginx-config.sh` script.

### Issue 2: Windows Authentication Not Working

**Problem:** Windows/AD authentication fails with "invalid credentials" even with correct credentials.

**Root Cause:** Missing environment variables in Docker container.

**Solution:**
1. Ensure all AD variables are in `.env` file:
   ```bash
   USE_WINDOWS_AUTH=true
   AD_SERVER=ldap://10.20.100.15
   AD_DOMAIN=kmc.int
   AD_BASE_DN=DC=kmc,DC=int
   AD_USER_SEARCH_BASE=DC=kmc,DC=int
   AD_GROUP_SEARCH_BASE=DC=kmc,DC=int
   ```

2. Verify `docker-compose.yml` includes all AD environment variables:
   - `AD_USER_SEARCH_BASE`
   - `AD_GROUP_SEARCH_BASE`
   - `AD_REQUIRED_GROUP` (optional)
   - `AD_SERVICE_USER` (optional)
   - `AD_SERVICE_PASSWORD` (optional)

3. Restart containers:
   ```bash
   docker compose down && docker compose up -d
   ```

**Testing:** Use the provided `debug-windows-auth.py` script to test authentication.

### Issue 3: PostgreSQL Migration Issues

**Problem:** Application fails to start due to JSON file dependencies.

**Root Cause:** Legacy code still referencing `switches.json` files.

**Solution:**
1. Complete PostgreSQL migration was implemented
2. All JSON references replaced with database calls
3. Database fallback functions implemented

**Status:** ✅ Resolved in current version

### Issue 4: Environment Variables Not Loading

**Problem:** Docker container doesn't pick up environment variables from `.env` file.

**Root Cause:** Variables not explicitly declared in `docker-compose.yml`.

**Solution:**
1. All required environment variables must be explicitly listed in the `environment:` section of `docker-compose.yml`
2. Use format: `- VARIABLE_NAME=${VARIABLE_NAME}`
3. Restart containers after changes

## 🔧 Troubleshooting Tools

### Quick Health Check
```bash
# Check application health
curl -k https://localhost/health

# Check direct application access
curl http://localhost:5000/health

# Check container status
docker compose ps

# Check logs
docker compose logs port-tracer --tail 50
```

### Windows Authentication Debug
```bash
# Test LDAP connection
docker compose exec port-tracer python3 test-ldap-connection.py

# Debug authentication with credentials
docker compose exec port-tracer python3 debug-windows-auth.py username password
```

### Nginx Troubleshooting
```bash
# Test nginx configuration
sudo nginx -t

# Check nginx error logs
tail -f /var/log/nginx/kmc-port-tracer.error.log

# Reload nginx
sudo nginx -s reload
```

## 📝 Deployment Checklist

### Pre-Deployment
- [ ] Update `.env` file with correct settings
- [ ] Verify `docker-compose.yml` includes all required environment variables
- [ ] Test LDAP connectivity to domain controller
- [ ] Backup existing configuration

### Post-Deployment
- [ ] Verify application health endpoint responds
- [ ] Test Windows authentication (if enabled)
- [ ] Check nginx proxy configuration
- [ ] Verify database connectivity
- [ ] Test switch management functionality

### Production Monitoring
- [ ] Monitor application logs: `docker compose logs port-tracer`
- [ ] Monitor nginx logs: `/var/log/nginx/kmc-port-tracer.error.log`
- [ ] Check container health: `docker compose ps`
- [ ] Verify database persistence: PostgreSQL data volume

## 🚀 Quick Recovery Commands

### Restart Application
```bash
cd port-tracing-script
docker compose restart port-tracer
```

### Full Rebuild (if needed)
```bash
cd port-tracing-script
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Rollback (emergency)
```bash
cd port-tracing-script
git checkout HEAD~1  # Go back one commit
docker compose down
docker compose build --no-cache
docker compose up -d
```

## 📞 Support Information

### Log Locations
- Application logs: `docker compose logs port-tracer`
- Nginx logs: `/var/log/nginx/kmc-port-tracer.error.log`
- System logs: `/var/log/syslog`

### Key Files
- Configuration: `.env`
- Compose: `docker-compose.yml`
- Nginx: `/etc/nginx/sites-enabled/kmc-port-tracer.conf`

Last Updated: August 2025
