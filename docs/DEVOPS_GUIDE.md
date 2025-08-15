# Dell Switch Port Tracer v2.1.3 - DevOps Guide

## 📋 Table of Contents
- [System Architecture](#system-architecture)
- [Deployment Methods](#deployment-methods)
- [Configuration Management](#configuration-management)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)
- [Security Considerations](#security-considerations)
- [Maintenance](#maintenance)

---

## 🏢 System Architecture (v2.1.3)

### **3-Container Docker Compose Stack**
```
┌─────────────────────────────────────────────────────────────────┐
│                     Dell Port Tracer v2.1.3                     │
│                   Production Architecture                        │
└─────────────────────────────────────────────────────────────────┘

          ┌────────────────────────────────────────┐
          │        Web Client (User Browser)         │
          │          HTML/CSS/JS + jQuery            │
          │         Role-based UI Elements           │
          └─────────────────────────┬───────────────┘
                                    │
                   HTTPS/SSL (Port 443)
                   HTTP→HTTPS Redirect (Port 80)
                                    │
                                    ▼
          ┌────────────────────────────────────────┐
          │      dell-port-tracer-nginx              │
          │  • SSL/HTTPS Termination                │
          │  • Reverse Proxy & Load Balancing       │
          │  • Security Headers                     │
          │  • Static File Serving                  │
          └─────────────────────────┬───────────────┘
                      Proxy Pass     │
                      (app:5000)     │
                                    ▼
          ┌────────────────────────────────────────┐
          │       dell-port-tracer-app              │
          │  • Flask Web Application                │
          │  • SSH to Dell Switches                 │
          │  • Windows AD/LDAP Authentication       │
          │  • Role-based Access Control            │
          │  • Port Tracing Logic (Netmiko)         │
          └─────────────────────────┬───────────────┘
                      PostgreSQL     │
                      Connection     │
                      (postgres:5432)│
                                    ▼
          ┌────────────────────────────────────────┐
          │     dell-port-tracer-postgres           │
          │  • PostgreSQL 15 Database               │
          │  • Switch Inventory Storage             │
          │  • Encrypted Credentials                 │
          │  • Comprehensive Audit Logs             │
          │  • Persistent Named Volume               │
          └────────────────────────────────────────┘

          ┌────────────────────────────────────────┐
          │              External Systems             │
          ├────────────────────────────────────────┤
          │  Dell Switches ◄── SSH (Port 22)         │
          │  Windows AD    ◄── LDAP (389/636)        │
          │  Syslog Server ◄── UDP (Port 514)        │
          └────────────────────────────────────────┘
```

### **Key Components**
- **Flask Application**: Python web service handling MAC tracing
- **Docker Container**: Isolated runtime environment
- **Kubernetes**: Orchestration and scaling (optional)
- **Windows AD Integration**: LDAP authentication
- **Switch Configuration**: JSON-based switch inventory
- **Concurrent Processing**: ThreadPoolExecutor for parallel operations

### **Data Flow**
1. User authenticates via AD/local accounts
2. Site/floor selection loads switch inventory
3. MAC address traced concurrently across switches
4. Results filtered by user role and returned
5. Actions logged for audit purposes

---

## 🚀 Deployment Methods

### **1. Docker Compose Deployment (Recommended)**

#### **Production 3-Container Stack**
```bash
# Clone repository
git clone https://github.com/Crispy-Pasta/DellPortTracer.git
cd DellPortTracer

# Configure environment
cp .env.example .env
# Edit .env with appropriate values

# Deploy production stack
docker-compose -f docker-compose.prod.yml up -d

# Verify deployment
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs
```

#### **Production Docker Compose Configuration**
```yaml
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    container_name: dell-port-tracer-nginx
    ports:
      - "80:80"      # HTTP (redirects to HTTPS)
      - "443:443"    # HTTPS
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl/private:ro
      - ./static:/usr/share/nginx/html/static:ro
    depends_on:
      - app
    networks:
      - dell-tracer-network
    restart: unless-stopped

  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: dell-port-tracer-app
    environment:
      - DATABASE_URL=postgresql://porttracer:${POSTGRES_PASSWORD}@postgres:5432/porttracer_db
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./data/switches:/app/data/switches:ro
    depends_on:
      postgres:
        condition: service_healthy
    networks:
      - dell-tracer-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:15-alpine
    container_name: dell-port-tracer-postgres
    environment:
      - POSTGRES_DB=porttracer_db
      - POSTGRES_USER=porttracer
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_INITDB_ARGS=--auth-host=md5
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d:ro
    networks:
      - dell-tracer-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U porttracer -d porttracer_db"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  postgres_data:
    driver: local

networks:
  dell-tracer-network:
    driver: bridge
```

### **2. Kubernetes Deployment**

#### **Basic Deployment**
```bash
# Apply configurations
kubectl apply -f k8s-secret.yaml
kubectl apply -f k8s-configmap.yaml
kubectl apply -f k8s-deployment.yaml
kubectl apply -f k8s-service.yaml
kubectl apply -f k8s-ingress.yaml

# Verify deployment
kubectl get pods -l app=dell-port-tracer
kubectl get services dell-port-tracer
```

#### **Scaling**
```bash
# Scale replicas
kubectl scale deployment dell-port-tracer --replicas=3

# Check status
kubectl rollout status deployment/dell-port-tracer
```

### **3. Bare Metal Deployment**

#### **System Requirements**
- **OS**: Ubuntu 20.04+ / RHEL 8+ / CentOS 8+
- **Python**: 3.11+
- **Memory**: 2GB minimum, 4GB recommended
- **Disk**: 10GB minimum
- **Network**: Access to Dell switches on SSH (port 22)

#### **Installation Steps**
```bash
# Install dependencies
sudo apt update
sudo apt install python3.11 python3-pip python3-venv

# Create application directory
sudo mkdir -p /opt/dell-port-tracer
cd /opt/dell-port-tracer

# Clone and setup
git clone https://github.com/Crispy-Pasta/DellPortTracer.git .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with appropriate values

# Create systemd service
sudo cp deploy/dell-port-tracer.service /etc/systemd/system/
sudo systemctl enable dell-port-tracer
sudo systemctl start dell-port-tracer
```

---

## ⚙️ Configuration Management

### **Environment Variables**

#### **Required Variables**
```bash
# Database Configuration
POSTGRES_PASSWORD=secure_db_password_123
DATABASE_URL=postgresql://porttracer:${POSTGRES_PASSWORD}@postgres:5432/porttracer_db

# Switch Credentials (AES-256 Encrypted)
SWITCH_USERNAME=admin
SWITCH_PASSWORD=encrypted_switch_password
CREDENTIALS_ENCRYPTION_KEY=your_32_char_encryption_key_here

# Web Authentication Passwords
OSS_PASSWORD=oss123
NETADMIN_PASSWORD=netadmin123
SUPERADMIN_PASSWORD=superadmin123
WEB_PASSWORD=password  # Legacy admin account

# SSL/TLS Configuration
SSL_CERT_PATH=/etc/ssl/private/porttracer.crt
SSL_KEY_PATH=/etc/ssl/private/porttracer.key
HTTPS_ENABLED=true

# Windows AD Integration (Optional)
USE_WINDOWS_AUTH=true
AD_SERVER=ldap://domain.com
AD_DOMAIN=domain.com
AD_BASE_DN=DC=domain,DC=com
AD_USER_SEARCH_BASE=DC=domain,DC=com
AD_GROUP_SEARCH_BASE=DC=domain,DC=com
AD_GROUP_MAPPING_OSS=OSS_Users
AD_GROUP_MAPPING_NETADMIN=NetAdmin_Users
AD_GROUP_MAPPING_SUPERADMIN=SuperAdmin_Users
```

#### **Performance Tuning Variables**
```bash
# Concurrent User Limits
MAX_CONCURRENT_USERS_PER_SITE=10    # Dell SSH session limit
MAX_WORKERS_PER_SITE=8              # Parallel connections

# Timeouts
SWITCH_SSH_TIMEOUT=15                # SSH connection timeout
TRACE_OPERATION_TIMEOUT=60           # Overall operation timeout

# Logging
LOG_LEVEL=INFO                       # DEBUG, INFO, WARNING, ERROR
LOG_RETENTION_DAYS=30                # Log file retention
```

### **Switch Configuration**

The `switches.json` file defines the switch inventory:

```json
{
  "sites": {
    "SITE_NAME": {
      "floors": {
        "FLOOR_NAME": {
          "switches": {
            "SWITCH_NAME": {
              "ip_address": "10.0.1.100",
              "model": "Dell N3248",
              "series": "N3200", 
              "port_category": {
                "access_ports": ["Te1/0/1-48"],
                "uplink_ports": ["Tw1/0/1-4"]
              },
              "enabled": true,
              "description": "Floor switch"
            }
          }
        }
      }
    }
  }
}
```

### **Auto-Deployment Configuration**

The auto-deployment script (`auto-deploy.sh`) provides:
- **Automatic Updates**: Pulls from GitHub every minute
- **Health Monitoring**: Restarts container if unhealthy
- **Change Detection**: Only deploys when files change
- **Logging**: All operations logged with timestamps

---

## 📊 Monitoring & Logging

### **Health Checks**

#### **Application Health**
```bash
# HTTP health check (via nginx)
curl -f https://localhost/health

# Direct application health check
curl -f http://localhost:5000/health

# Expected response
{
  "status": "healthy",
  "version": "2.1.3", 
  "timestamp": "2025-01-27T21:00:00Z",
  "sites_count": 27,
  "windows_auth": true,
  "database": "connected",
  "database_type": "PostgreSQL 15",
  "switch_inventory": "loaded",
  "encryption_status": "enabled"
}
```

#### **Container Health (3-Container Stack)**
```bash
# Check all containers in the stack
docker-compose -f docker-compose.prod.yml ps

# Individual container status
docker ps --filter name=dell-port-tracer

# Container logs
docker logs dell-port-tracer-nginx --tail 50
docker logs dell-port-tracer-app --tail 50
docker logs dell-port-tracer-postgres --tail 50

# Combined logs from all services
docker-compose -f docker-compose.prod.yml logs --tail=50

# Kubernetes health check  
kubectl get pods -l app=dell-port-tracer
kubectl describe pod <pod-name>
```

#### **Database Health**
```bash
# PostgreSQL connection test
docker exec dell-port-tracer-postgres pg_isready -U porttracer -d porttracer_db

# Database size and connection info
docker exec dell-port-tracer-postgres psql -U porttracer -d porttracer_db -c "\l+"
docker exec dell-port-tracer-postgres psql -U porttracer -d porttracer_db -c "SELECT count(*) FROM pg_stat_activity;"

# Expected healthy responses
# pg_isready: accepting connections
# Connection count should be reasonable (typically < 20)
```

### **Log Files**

#### **Application Logs**
- **`port_tracer.log`**: System events, errors, performance metrics
- **`audit.log`**: User actions, authentication, MAC traces
- **`auto-deploy.log`**: Deployment and health check activities

#### **Log Formats**
```
# System Log Format
2025-07-24 21:00:00,000 - INFO - User: admin - MAC Trace Started - MAC: 00:1B:63:84:45:E6

# Audit Log Format  
2025-07-24 21:00:00,000 - AUDIT - User: janestrada (netadmin) - LOGIN SUCCESS via windows_ad

# Performance Log Format
2025-07-24 21:00:05,000 - INFO - MAC trace progress: 8/10 switches completed
2025-07-24 21:00:07,000 - AUDIT - User: janestrada - MAC Trace Completed - Results: 1 found - Time: 7.23s - Workers: 8
```

### **Monitoring Metrics**

#### **Key Performance Indicators**
- **Response Time**: MAC trace execution time (target: <10s)
- **Concurrent Users**: Per-site user count (limit: 10)
- **Success Rate**: Successful traces vs. total attempts
- **Switch Connectivity**: SSH connection success rate
- **Authentication Rate**: Login success rate

#### **Alert Thresholds**
```bash
# Performance Alerts
TRACE_TIME_WARNING=15s      # Warn if trace takes >15s
TRACE_TIME_CRITICAL=30s     # Critical if trace takes >30s
CONCURRENT_USERS_WARNING=8  # Warn at 8/10 concurrent users
SWITCH_FAILURE_RATE=20%     # Alert if >20% switches fail

# System Alerts
MEMORY_USAGE_WARNING=80%    # Warn at 80% memory usage
DISK_USAGE_WARNING=85%      # Warn at 85% disk usage
CPU_USAGE_WARNING=75%       # Warn at 75% CPU usage
```

---

## 🔧 Troubleshooting

### **Common Issues**

#### **1. Container Stack Won't Start**
```bash
# Check all containers in the stack
docker-compose -f docker-compose.prod.yml ps

# Check individual container logs
docker logs dell-port-tracer-nginx --tail 50
docker logs dell-port-tracer-app --tail 50
docker logs dell-port-tracer-postgres --tail 50

# Common causes and solutions:
# - Missing .env file: Create from .env.example
# - Invalid POSTGRES_PASSWORD: Check environment variables
# - SSL certificate issues: Verify cert/key files exist
# - Port conflicts: Ensure ports 80, 443, 5432 available
# - Permission issues: Check file ownership and Docker socket access
# - Network conflicts: Ensure dell-tracer-network is available

# Restart the entire stack
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# Restart individual services
docker-compose -f docker-compose.prod.yml restart nginx
docker-compose -f docker-compose.prod.yml restart app
docker-compose -f docker-compose.prod.yml restart postgres
```

#### **2. Database Connection Issues**
```bash
# Check PostgreSQL container status
docker logs dell-port-tracer-postgres --tail 50

# Test database connectivity
docker exec dell-port-tracer-postgres pg_isready -U porttracer -d porttracer_db

# Connect to database directly
docker exec -it dell-port-tracer-postgres psql -U porttracer -d porttracer_db

# Common database issues:
# - Wrong POSTGRES_PASSWORD in .env
# - Database not initialized: Check init-scripts volume
# - Connection limit reached: Check active connections
# - Disk space full: Check postgres_data volume
# - Network connectivity: Ensure app can reach postgres container

# Reset database if needed (WARNING: destroys all data)
docker-compose -f docker-compose.prod.yml down
docker volume rm postgres_data
docker-compose -f docker-compose.prod.yml up -d
```

#### **2. Authentication Issues**

**Windows AD Problems:**
```bash
# Test LDAP connectivity
ldapsearch -x -H ldap://domain.com -D "user@domain.com" -W

# Check AD configuration in .env
grep AD_ .env

# Common fixes:
# - Verify AD_SERVER URL
# - Check AD_BASE_DN format
# - Confirm network connectivity to domain controller
# - Validate service account permissions
```

**Local Authentication Problems:**
```bash
# Check user configuration
grep -A5 "USERS = {" port_tracer_web.py

# Reset passwords in .env
OSS_PASSWORD=new_password
NETADMIN_PASSWORD=new_password
```

#### **3. Switch Connectivity Issues**

**SSH Connection Failures:**
```bash
# Test SSH manually
ssh switch_username@switch_ip

# Check switch configuration
grep SWITCH_ .env

# Network troubleshooting
ping switch_ip
telnet switch_ip 22
traceroute switch_ip

# Common fixes:
# - Verify switch credentials
# - Check firewall rules
# - Confirm SSH enabled on switches
# - Validate network routing
```

#### **4. Performance Issues**

**Slow MAC Tracing:**
```bash
# Check concurrent user limits
grep "Concurrent user limit" /app/logs/audit.log

# Monitor worker utilization
grep "Concurrent workers" /app/logs/audit.log

# Performance tuning:
# - Increase MAX_WORKERS_PER_SITE (max 8)
# - Check network latency to switches
# - Reduce MAX_CONCURRENT_USERS_PER_SITE if needed
# - Monitor system resources
```

#### **5. Memory Issues**

**Container Memory Problems:**
```bash
# Check container memory usage
docker stats dell-port-tracer

# Check application memory usage
docker exec dell-port-tracer ps aux | grep python

# Solutions:
# - Increase container memory limits
# - Reduce concurrent workers
# - Check for memory leaks in logs
# - Restart container periodically
```

### **Debug Mode**

#### **Enable Debug Logging**
```bash
# Add to .env file
LOG_LEVEL=DEBUG

# Restart application
docker restart dell-port-tracer

# Monitor debug logs
docker logs -f dell-port-tracer | grep DEBUG
```

#### **Manual Testing**
```bash
# Test switch SSH connection
docker exec -it dell-port-tracer python3 -c "
from port_tracer_web import DellSwitchSSH
import os
switch = DellSwitchSSH('SWITCH_IP', os.getenv('SWITCH_USERNAME'), os.getenv('SWITCH_PASSWORD'))
print('Connection:', switch.connect())
switch.disconnect()
"

# Test AD authentication
docker exec -it dell-port-tracer python3 -c "
from nt_auth_integration import WindowsAuthenticator
auth = WindowsAuthenticator({'server': 'ldap://domain.com', 'domain': 'domain.com'})
result = auth.authenticate_user('username', 'password')
print('Auth result:', result)
"
```

---

## ⚡ Performance Tuning

### **Application Optimization**

#### **Concurrent Processing**
```python
# Environment variables for tuning
MAX_CONCURRENT_USERS_PER_SITE=10    # Dell switch SSH limit
MAX_WORKERS_PER_SITE=8              # Optimal for most deployments

# For high-performance environments:
MAX_WORKERS_PER_SITE=12             # May cause Dell switch overload
SWITCH_SSH_TIMEOUT=10               # Faster timeout for unreachable switches
```

#### **Memory Optimization**
```bash
# Docker memory limits
docker run --memory=2g --memory-swap=2g dell-port-tracer

# Kubernetes resource limits
resources:
  limits:
    memory: "2Gi"
    cpu: "1000m"
  requests:
    memory: "1Gi" 
    cpu: "500m"
```

### **Infrastructure Scaling**

#### **Horizontal Scaling**
```bash
# Kubernetes scaling
kubectl scale deployment dell-port-tracer --replicas=3

# Load balancer configuration for session affinity
apiVersion: v1
kind: Service
metadata:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: nlb
spec:
  sessionAffinity: ClientIP
```

#### **Database Optimization**
```bash
# Switch inventory caching
# Cache switches.json in memory for faster access
# Implement Redis caching for large deployments

# Log rotation
LOG_RETENTION_DAYS=7                # Reduce log retention
MAX_LOG_SIZE=100MB                  # Limit individual log file size
```

---

## 🔒 Security Considerations

### **Network Security**

#### **Firewall Rules**
```bash
# Inbound rules
8443/tcp    # Web interface access
22/tcp      # SSH for management (restrict source)

# Outbound rules  
22/tcp      # SSH to Dell switches
389/tcp     # LDAP to domain controllers
636/tcp     # LDAPS (secure LDAP)
443/tcp     # HTTPS for external dependencies
```

#### **SSL/TLS Configuration**
```nginx
# nginx reverse proxy with SSL
server {
    listen 443 ssl http2;
    server_name porttracer.company.com;
    
    ssl_certificate /etc/ssl/certs/porttracer.crt;
    ssl_certificate_key /etc/ssl/private/porttracer.key;
    
    location / {
        proxy_pass http://dell-port-tracer:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### **Application Security**

#### **Credential Management**
```bash
# Environment variables (never hardcode)
SWITCH_USERNAME=admin
SWITCH_PASSWORD=${SWITCH_PASS_SECRET}

# Kubernetes secrets
kubectl create secret generic dell-tracer-secret \
  --from-literal=switch-username=admin \
  --from-literal=switch-password=secure_password
```

#### **Access Control**
```python
# Role-based filtering enforced at application level
# OSS users: No uplink ports, limited VLAN info
# NetAdmin: Full network access
# SuperAdmin: Complete system access

# Session management with secure cookies
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
```

### **Audit & Compliance**

#### **Audit Trail Requirements**
- All user authentication attempts logged
- MAC trace operations with timestamps
- Switch access attempts and results
- Administrative actions tracked
- Performance metrics for compliance

#### **Data Retention**
```bash
# Log retention policy
AUDIT_LOG_RETENTION=90days         # Compliance requirement
SYSTEM_LOG_RETENTION=30days        # Operational logs
PERFORMANCE_LOG_RETENTION=7days     # Metrics and monitoring
```

---

## 🛠️ Maintenance

### **Regular Maintenance Tasks**

#### **Daily Tasks**
```bash
# Health check verification
curl -f http://localhost:8443/health

# Log file monitoring
tail -n 100 /app/logs/port_tracer.log | grep ERROR
tail -n 100 /app/logs/audit.log | grep FAILED

# Container resource usage
docker stats dell-port-tracer --no-stream
```

#### **Weekly Tasks**
```bash
# Switch inventory validation
python3 validate_switches.py

# Performance metrics review
grep "Time:" /app/logs/audit.log | awk '{print $NF}' | sort -n

# Security log review
grep "LOGIN FAILED" /app/logs/audit.log

# Update checks
git fetch origin
git log HEAD..origin/main --oneline
```

#### **Monthly Tasks**  
```bash
# Log rotation and cleanup
find /app/logs -type f -mtime +30 -delete

# Switch model verification
python3 check_switch_models.py

# Performance optimization review
# - Analyze average trace times
# - Review concurrent user patterns
# - Check resource utilization trends

# Security updates
docker pull python:3.11-slim
docker build --no-cache -t dell-port-tracer:latest .
```

### **Backup & Recovery**

#### **Configuration Backup**
```bash
# Backup essential files
tar -czf dell-tracer-backup-$(date +%Y%m%d).tar.gz \
  .env \
  switches.json \
  static/ \
  *.py \
  requirements.txt \
  Dockerfile \
  k8s-*.yaml

# Upload to secure storage
aws s3 cp dell-tracer-backup-*.tar.gz s3://backups/dell-tracer/
```

#### **Disaster Recovery**
```bash
# Recovery procedure
1. Restore configuration files from backup
2. Verify switches.json integrity
3. Test switch connectivity
4. Rebuild and deploy container/pods
5. Verify authentication systems
6. Run health checks
7. Notify users when service restored
```

### **Updates & Patches**

#### **Application Updates**
```bash
# Automated updates via auto-deploy script
# - Monitors GitHub repository every minute
# - Downloads file changes automatically
# - Rebuilds container if code changes detected
# - Restarts service with zero-downtime rolling update

# Manual update process
git pull origin main
docker build -t dell-port-tracer:latest .
docker stop dell-port-tracer
docker rm dell-port-tracer
docker run -d --name dell-port-tracer [options] dell-port-tracer:latest
```

#### **Dependency Updates** 
```bash
# Python package updates
pip list --outdated
pip install --upgrade -r requirements.txt

# Security updates
docker pull python:3.11-slim
apt update && apt upgrade -y
```

---

## 📞 Support & Escalation

### **Support Tiers**

1. **L1 - Application Issues**: Basic troubleshooting, restarts, log review
2. **L2 - Infrastructure Issues**: Container/K8s issues, network problems
3. **L3 - Development Issues**: Code bugs, feature requests, architecture changes

### **Emergency Procedures**

#### **Service Down**
```bash
1. Check container status: docker ps | grep dell-port-tracer
2. Check logs: docker logs dell-port-tracer --tail 100
3. Restart container: docker restart dell-port-tracer
4. If persistent, escalate to L2
5. Check auto-deploy logs: tail -f /home/janzen/auto-deploy.log
```

#### **Performance Degradation**
```bash
1. Check concurrent user limits in audit logs
2. Monitor system resources: top, free -h, df -h
3. Review network connectivity to switches
4. Check for switch maintenance windows
5. Scale resources if needed
```

### **Contact Information**
- **Repository**: https://github.com/Crispy-Pasta/DellPortTracer
- **Documentation**: README.md, USER_GUIDE.md, DEPLOYMENT.md
- **Issues**: GitHub Issues for bug reports and feature requests

---

*This DevOps guide is maintained alongside the application. For the latest version, check the repository documentation.*
