# Dell Port Tracer - Development Team Architecture

## 👨‍💻 Development Team Overview

This documentation targets software developers and application architects, focusing on the application architecture, code structure, APIs, and data flow of the Dell Port Tracer.

## Application Architecture Diagram (v2.1.3)

```
┌─────────────────────────────────────────────────────────────────┐
│               APPLICATION ARCHITECTURE v2.1.3                   │
│                   3-Container Production Stack                   │
└─────────────────────────────────────────────────────────────────┘

          ┌──────────────────────────────────────────┐
          │        Web Client (User Browser)         │
          │          HTML/CSS/JS + jQuery            │
          │         Role-based UI Elements           │
          └─────────────────────────┬────────────────┘
                                    │
                   HTTPS/SSL (Port 443)
                   HTTP→HTTPS Redirect (Port 80)
                                    │
                                    ▼
          ┌─────────────────────────────────────────────┐
          │         dell-port-tracer-nginx              │
          │    • SSL/HTTPS Termination                  │
          │    • Reverse Proxy & Load Balancing         │
          │    • Security Headers                       │
          │    • Static File Serving                    │
          │    • Health Check Endpoint                  │
          └─────────────────────────┬───────────────────┘
                      Proxy Pass     │
                      (app:5000)     │
                                    ▼
          ┌─────────────────────────────────────────────┐
          │         dell-port-tracer-app                │
          │    • Flask Web Application                  │
          │    • Dell Switch SSH Connections           │
          │    • Windows AD/LDAP Authentication        │
          │    • Role-based Access Control             │
          │    • Port Tracing Logic                     │
          │    • MAC Address Processing                 │
          │    • Sidebar Height Fix (min-height:400px) │
          └─────────────────────────┬───────────────────┘
                      PostgreSQL     │
                      Connection     │
                      (postgres:5432)│
                                    ▼
          ┌─────────────────────────────────────────────┐
          │       dell-port-tracer-postgres             │
          │    • PostgreSQL 15 Database                 │
          │    • Persistent Named Volume                │
          │    • Automatic Backup Integration           │
          │    • Health Checks (pg_isready)             │
          │    • Switch Inventory & Audit Logs         │
          └─────────────────────────────────────────────┘

          ┌─────────────────────────────────────────────┐
          │              External Systems               │
          ├─────────────────────────────────────────────┤
          │  Dell Switches ◄── SSH (Port 22)           │
          │  Windows AD    ◄── LDAP (389/636)          │
          │  Syslog Server ◄── UDP (Port 514)          │
          └─────────────────────────────────────────────┘
```

## Code Structure

### Project Layout (v2.1.3)

```
DellPortTracer/
├── port_tracer_web.py          # Main Flask application
├── templates/
│   └── index.html              # Single-page application template
├── static/
│   ├── css/
│   │   └── style.css           # Main stylesheet with sidebar fixes
│   └── js/
│       └── app.js              # Frontend JavaScript with jQuery
├── tools/                      # Debug and maintenance scripts
│   ├── test_ldap_connection.py # LDAP connectivity tester
│   ├── test_ad_auth.py         # AD authentication tester
│   ├── nginx_fix.py            # nginx configuration fix
│   └── debug_env.py            # Environment variable debug
├── docs/
│   ├── README.md               # Updated deployment documentation
│   └── troubleshooting.md      # Docker/SSL troubleshooting guide
├── architecture/               # Architecture documentation
│   ├── dev-team.md             # Development team architecture
│   └── network-team.md         # Network team architecture
├── nginx/                      # nginx configuration
│   └── nginx.conf              # SSL/proxy configuration
├── init_db.py                  # Database initialization script
├── migrate_data.py             # SQLite to PostgreSQL migration
├── Dockerfile                  # Docker container definition
├── docker-compose.yml          # 3-container production stack
├── scripts/                    # Deployment automation
│   ├── deploy.sh               # Safe deployment script
│   ├── backup.sh               # Database backup script
│   └── ssl-setup.sh            # SSL certificate setup
├── requirements.txt            # Python dependencies
└── .env.example               # Environment variable template
```

### Key Components

- **`port_tracer_web.py`**: Main Flask application with all routes and business logic
- **`templates/index.html`**: Single-page application with embedded template logic
- **`static/`**: CSS and JavaScript assets for the frontend
- **`tools/`**: Debugging and maintenance utilities
- **`init_db.py`**: Database schema initialization
- **`migrate_data.py`**: Data migration utilities

## Data Flow

### API Endpoints (v2.1.3)

1. **Authentication**:
   - `POST /api/login` - User authentication via Windows AD/LDAP
   - `POST /api/logout` - Session termination
   - `GET /api/user` - Current user information

2. **Port Tracing**:
   - `POST /api/trace_port` - Trace a MAC address through the network
   - `GET /api/trace_history` - View port trace history
   - `DELETE /api/trace/{id}` - Delete a specific trace record

3. **Switch Management**:
   - `GET /api/switches` - List all switches
   - `POST /api/switches` - Add new switch
   - `PUT /api/switches/{id}` - Update switch configuration
   - `DELETE /api/switches/{id}` - Remove switch
   - `GET /api/switches/{id}/ports` - Get switch port information

4. **System Health**:
   - `GET /health` - Application health check
   - `GET /api/system/status` - Detailed system status
   - `GET /api/system/stats` - Usage statistics

### Database Models (v2.1.3)

```python
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Switch(db.Model):
    __tablename__ = 'switches'

    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(15), nullable=False, unique=True)
    ssh_username = db.Column(db.String(100), nullable=False)
    ssh_password = db.Column(db.String(255), nullable=False)  # Encrypted
    device_type = db.Column(db.String(50), default='dell_os10')
    site = db.Column(db.String(100))
    floor = db.Column(db.String(50))
    building = db.Column(db.String(100))
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PortTrace(db.Model):
    __tablename__ = 'port_traces'

    id = db.Column(db.Integer, primary_key=True)
    switch_id = db.Column(db.Integer, db.ForeignKey('switches.id'), nullable=False)
    mac_address = db.Column(db.String(17), nullable=False)
    ip_address = db.Column(db.String(15))
    port_name = db.Column(db.String(50))
    vlan_id = db.Column(db.Integer)
    trace_result = db.Column(db.Text)  # JSON string of full trace results
    user_id = db.Column(db.String(100))  # AD username
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    display_name = db.Column(db.String(200))
    email = db.Column(db.String(200))
    role = db.Column(db.String(50), default='user')  # user, admin, readonly
    department = db.Column(db.String(100))
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # login, trace_port, add_switch, etc.
    resource_type = db.Column(db.String(50))  # switch, port_trace, user
    resource_id = db.Column(db.String(50))
    details = db.Column(db.Text)  # JSON string with additional details
    ip_address = db.Column(db.String(15))
    user_agent = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
```

## Docker Deployment Architecture (v2.1.3)

### Container Specifications

#### nginx Container (`dell-port-tracer-nginx`)
```yaml
services:
  nginx:
    image: nginx:alpine
    container_name: dell-port-tracer-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### Flask Application Container (`dell-port-tracer-app`)
```yaml
services:
  app:
    build: .
    container_name: dell-port-tracer-app
    environment:
      - FLASK_ENV=production
      - DATABASE_URL=postgresql://username:password@postgres:5432/dell_port_tracer
      - LDAP_SERVER=${LDAP_SERVER}
      - LDAP_DOMAIN=${LDAP_DOMAIN}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### PostgreSQL Database Container (`dell-port-tracer-postgres`)
```yaml
services:
  postgres:
    image: postgres:15-alpine
    container_name: dell-port-tracer-postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 30s
      timeout: 10s
      retries: 5

volumes:
  postgres_data:
    name: dell_port_tracer_postgres_data
```

### Environment Configuration

#### Required Environment Variables
```bash
# Database Configuration
POSTGRES_DB=dell_port_tracer
POSTGRES_USER=port_tracer_user
POSTGRES_PASSWORD=secure_random_password_here
DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}

# Flask Application
FLASK_ENV=production
SECRET_KEY=generate_strong_secret_key_here
FLASK_DEBUG=False

# LDAP/AD Authentication
LDAP_SERVER=ldap://your-domain-controller.company.com
LDAP_DOMAIN=COMPANY
LDAP_BASE_DN=DC=company,DC=com
LDAP_USER_SEARCH_BASE=OU=Users,DC=company,DC=com

# Dell Switch Credentials (encrypted in database)
DEFAULT_SSH_USERNAME=admin
DEFAULT_SSH_PASSWORD=encrypted_password

# SSL Configuration
SSL_CERT_PATH=/etc/nginx/ssl/cert.pem
SSL_KEY_PATH=/etc/nginx/ssl/key.pem

# Logging
LOG_LEVEL=INFO
SYSLOG_SERVER=your-syslog-server.company.com
SYSLOG_PORT=514
```

## API Integration

### Authentication

- **JWT Tokens**: Secure access to API endpoints
- **LDAP Authentication**: Enable login via Active Directory
- **Role-based Access Control**: Admin, User, and ReadOnly roles
- **Session Management**: Secure session handling with Redis (optional)

### External Libraries (v2.1.3)

```python
# Core Framework
Flask==2.3.3
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.5
Flask-JWT-Extended==4.5.3

# Database
psycopg2-binary==2.9.7
SQLAlchemy==2.0.21

# Authentication
Flask-LDAP3-Login==0.9.18
ldap3==2.9.1

# SSH Connectivity
paramiko==3.3.1
netmiko==4.2.0

# Web Server
Gunicorn==21.2.0
gevent==23.7.0

# Security
cryptography==41.0.4
bcrypt==4.0.1

# Utilities
requests==2.31.0
python-dotenv==1.0.0
pytest==7.4.2
flake8==6.1.0
```

## Port Tracing Algorithm (v2.1.3)

### Workflow Overview

```python
def trace_mac_address(mac_address):
    """
    Trace a MAC address through the Dell switch network
    """
    # 1. Validate and normalize MAC address format
    normalized_mac = normalize_mac_address(mac_address)
    
    # 2. Query all active switches from database
    active_switches = get_active_switches()
    
    # 3. Connect to each switch via SSH and search MAC table
    for switch in active_switches:
        try:
            # Establish SSH connection using Netmiko
            connection = establish_ssh_connection(switch)
            
            # Execute MAC address table command
            mac_table = connection.send_command('show mac address-table')
            
            # Parse output for target MAC address
            if normalized_mac in mac_table:
                port_info = extract_port_information(mac_table, normalized_mac)
                
                # Get additional port details
                port_details = get_port_details(connection, port_info['port'])
                
                # Log the trace result
                log_trace_result(switch.id, normalized_mac, port_info, user_id)
                
                return {
                    'success': True,
                    'switch': switch.hostname,
                    'port': port_info['port'],
                    'vlan': port_info['vlan'],
                    'port_description': port_details.get('description'),
                    'port_status': port_details.get('status')
                }
                
        except SSHException as e:
            log_ssh_error(switch.id, str(e))
            continue
    
    return {'success': False, 'message': 'MAC address not found'}
```

### Key Components

1. **MAC Address Normalization**: Convert various MAC formats to consistent format
2. **SSH Connection Management**: Secure connections to Dell switches using Netmiko
3. **Command Parsing**: Extract relevant data from Dell OS10 command outputs
4. **Error Handling**: Robust handling of network timeouts and authentication failures
5. **Audit Logging**: Complete audit trail of all trace operations

## Security Considerations (v2.1.3)

### Authentication & Authorization

- **Windows AD Integration**: Single sign-on with corporate directory
- **Multi-factor Authentication**: Optional MFA support via LDAP attributes
- **Role-based Access Control**: Granular permissions for different user types
- **Session Security**: Secure JWT tokens with configurable expiration

### Data Protection

- **Encryption at Rest**: Database credentials encrypted using Fernet
- **Encryption in Transit**: All communications over HTTPS/SSL
- **SSH Key Management**: Secure storage of switch access credentials
- **Audit Logging**: Complete activity logs for compliance

### Network Security

```python
# SSH Connection Security Settings
SSH_CONFIG = {
    'device_type': 'dell_os10',
    'timeout': 30,
    'auth_timeout': 30,
    'banner_timeout': 15,
    'conn_timeout': 10,
    'keepalive': 30,
    'default_enter': '\r\n',
    'response_return': '\n',
    'serial_settings': {
        'rtscts': False,
        'dsrdtr': False,
    },
    'fast_cli': False,
    'global_delay_factor': 1,
    'use_keys': True,
    'key_file': '/app/ssh_keys/dell_switch_key',
    'allow_agent': False,
    'ssh_strict': True,
    'system_host_keys': True,
    'alt_host_keys': True,
    'alt_key_file': '/app/ssh_keys/known_hosts'
}
```

### Container Security

- **Non-root User**: Application runs as non-privileged user
- **Read-only Filesystem**: Container filesystem mounted as read-only where possible
- **Resource Limits**: CPU and memory limits enforced
- **Security Scanning**: Regular vulnerability scans of container images

## Deployment Workflow (v2.1.3)

### Development to Production Pipeline

```bash
# 1. Development Environment
git checkout -b feature/new-functionality
# Make changes, test locally
pytest tests/
flake8 .

# 2. Create Pull Request
git push origin feature/new-functionality
# Code review process

# 3. Merge to Main Branch
git checkout main
git pull origin main

# 4. Production Deployment
./scripts/deploy.sh
# This script:
# - Creates backup of current database
# - Builds new container image
# - Updates containers with zero-downtime
# - Runs health checks
# - Rollback if issues detected
```

### Safe Deployment Script

```bash
#!/bin/bash
# scripts/deploy.sh - Safe production deployment

set -e

echo "Starting safe deployment process..."

# 1. Create database backup
echo "Creating database backup..."
./scripts/backup.sh

# 2. Build new application image
echo "Building new application image..."
docker-compose build app

# 3. Update containers with rolling deployment
echo "Updating containers..."
docker-compose up -d --no-deps app

# 4. Wait for health check
echo "Waiting for application to be healthy..."
for i in {1..30}; do
    if curl -f http://localhost/health > /dev/null 2>&1; then
        echo "Application is healthy!"
        break
    fi
    echo "Waiting for health check... ($i/30)"
    sleep 10
done

# 5. Update nginx (if needed)
echo "Updating nginx configuration..."
docker-compose up -d nginx

echo "Deployment completed successfully!"
```

## Development Practices

### Code Quality

- **Testing**: Pytest framework with test cases for routes and models
- **Linting**: Use of flake8 to enforce PEP8 style guidelines
- **Type Hints**: Python type hints for better code documentation
- **Documentation**: Comprehensive docstrings following Google style
- **Continuous Integration**: GitHub Actions for automated testing

### Contribution Guidelines

- **Branching Model**: GitFlow with feature branches from main
- **Pull Requests**: Mandatory code review with minimum 2 approvals
- **Commit Messages**: Follow Conventional Commits standard
- **Testing Requirements**: All new features must include unit tests
- **Security Review**: Security-sensitive changes require additional review
