# Switch Port Manager v2.1.3

> **Note:** Repository migrated from `DellPortTracer` to `SwitchPortManager` for better organization and expanded functionality.

## 🚀 **Enterprise-Grade MAC Address Tracing Solution**

A secure, scalable web application for tracing MAC addresses across Dell switches in enterprise environments with advanced monitoring, protection, and logging capabilities. Enhanced security features including input validation and sanitized error messages.

![Version](https://img.shields.io/badge/version-2.1.3-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)
![Security](https://img.shields.io/badge/security-enhanced-green)

## 🚀 Features

### 🔐 Security Features
- **Enhanced Input Validation**: Comprehensive MAC address format validation with security-focused error messages
- **Sanitized Error Responses**: Error messages exclude potentially harmful examples or security-sensitive information
- **Command Injection Prevention**: Robust input sanitization to prevent malicious command execution
- **Role-Based Access Control**: Three security levels with least-privilege access patterns
- **Session Security**: Configurable session cookie security settings for HTTP/HTTPS deployments

### 🏢 Enterprise Management
- **Multi-Site Management**: Support for multiple sites and floors with centralized switch inventory
- **Comprehensive Management Interface**: Tabbed interface for managing Sites, Floors, and Switches with full CRUD operations
- **Site & Floor Administration**: Create, edit, and delete sites and floors with proper hierarchical relationships
- **Database-Driven Architecture**: PostgreSQL database for enterprise-grade scalability and reliability
- **Automatic Database Initialization**: Zero-configuration database setup on first deployment
- **Switch Management UI**: Web-based CRUD interface for network administrators to manage switches, sites, and floors
- **Database Migration Support**: Seamless migration from SQLite to PostgreSQL with data integrity validation
- **Windows AD Integration**: Secure LDAP authentication with role-based access control  
- **VLAN Manager**: Advanced VLAN configuration and port management capabilities

### 🔧 Technical Features
- **Dell Switch Support**: Comprehensive support for Dell N2000, N3000, and N3200 series switches (including N2048, N3248, N3024P models)
- **Intelligent Filtering**: Automatic uplink port detection and VLAN information filtering
- **Comprehensive Audit Logging**: Full activity tracking for security and compliance with syslog support
- **Responsive Web Interface**: Clean, modern UI with real-time MAC address tracing
- **Port Configuration Details**: Detailed port mode, VLAN, and description information
- **Container Ready**: Docker and Kubernetes deployment support with enhanced health checks
- **Production Ready**: Health checks, monitoring, and high availability
- **CPU Protection**: Advanced CPU monitoring and request throttling
- **Switch Protection**: Connection limits and rate limiting for switch protection

## 📋 Requirements

### System Requirements
- Python 3.8+
- PostgreSQL 12+ (or Docker for containerized database)
- Docker (for containerized deployment)
- Kubernetes cluster (for production deployment)
- Network access to Dell switches via SSH

### Python Dependencies
```bash
pip install -r requirements.txt
```

### Dell Switch Requirements
- SSH access enabled
- MAC address table accessible via CLI
- **Supported Switch Series**:
  - **N2000 Series**: N2048 and similar models (GigE access ports, 10GE uplinks)
  - **N3000 Series**: N3024P and similar models (GigE access ports, 10GE uplinks)
  - **N3200 Series**: N3248 and similar models (10GE access ports, 25GE uplinks)
- Auto-detection of switch models for proper port categorization

## 🚀 Quick Start Deployment

### Option 1: Docker Deployment (Recommended)

1. **Clone and Setup**
   ```bash
   git clone https://github.com/Crispy-Pasta/SwitchPortManager.git
   cd SwitchPortManager
   cp .env.example .env
   ```

2. **Configure Environment Variables**
   Edit the `.env` file with your specific configuration:
   ```env
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

3. **Deploy with Docker Compose**
   ```bash
   # Development deployment
   docker-compose up -d

   # Production deployment with enhanced security and health checks
   docker-compose -f docker-compose.prod.yml up -d

   # Monitor the startup process
   docker-compose logs -f app
   ```

4. **Access the Application**
   - **Development**: http://localhost:5000
   - **Default Login**: Username: `admin`, Password: `password` (or your configured `WEB_PASSWORD`)

### Option 2: Standard Python Deployment

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Crispy-Pasta/SwitchPortManager.git
   cd SwitchPortManager
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   Create a `.env` file:
   ```env
   # PostgreSQL Database Configuration
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   POSTGRES_DB=port_tracer_db
   POSTGRES_USER=dell_tracer_user
   POSTGRES_PASSWORD=secure_password_here

   # Dell Switch SSH Credentials
   SWITCH_USERNAME=your_switch_username
   SWITCH_PASSWORD=your_switch_password

   # Application Security
   SECRET_KEY=your_generated_secret_key
   SESSION_COOKIE_SECURE=false
   SESSION_COOKIE_HTTPONLY=true
   SESSION_COOKIE_SAMESITE=Lax
   PERMANENT_SESSION_LIFETIME=5

   # Web Service Configuration
   OSS_PASSWORD=oss123
   NETADMIN_PASSWORD=netadmin123
   SUPERADMIN_PASSWORD=superadmin123
   WEB_PASSWORD=admin_password_here
   ```

4. **Setup PostgreSQL Database**
   
   **Using Docker (Recommended)**
   ```bash
   docker run -d --name port-tracer-postgres \
     -e POSTGRES_DB=port_tracer_db \
     -e POSTGRES_USER=dell_tracer_user \
     -e POSTGRES_PASSWORD=secure_password_here \
     -p 5432:5432 postgres:15
   ```
   
   **Using Existing PostgreSQL Server**
   ```sql
   CREATE DATABASE port_tracer_db;
   CREATE USER dell_tracer_user WITH PASSWORD 'secure_password_here';
   GRANT ALL PRIVILEGES ON DATABASE port_tracer_db TO dell_tracer_user;
   ```

5. **Initialize Database Schema**
   ```bash
   # The database schema is initialized automatically on first run
   # Or initialize manually with:
   python init_db.py
   ```

6. **Start the Application**
   ```bash
   python port_tracer_web.py
   ```

## 🆕 What's New in v2.1.3

### ✅ **Automatic Database Initialization**
- **Zero Configuration Setup**: Database schema creates automatically on first deployment
- **Container-Ready**: Built-in database connection retry logic for Docker environments
- **Production Safe**: Idempotent initialization prevents duplicate table creation
- **Comprehensive Logging**: Detailed startup logs for troubleshooting

### ✅ **Enhanced Session Security**
- **Configurable Cookie Settings**: Environment-based session cookie configuration
- **HTTP/HTTPS Compatibility**: Proper cookie security for both HTTP and HTTPS deployments
- **Session Timeout Control**: Configurable session lifetime (default: 5 minutes)
- **Security Best Practices**: HttpOnly and SameSite cookie policies

### ✅ **Production-Grade Health Checks**
- **Database Connectivity**: Health checks verify actual database connections
- **Schema Validation**: Ensures required database tables exist and are accessible
- **Application Readiness**: Multi-layer health validation for container orchestration
- **Enhanced Monitoring**: Detailed health check logging for operations teams

### ✅ **Security Enhancements**
- **Data Protection**: Automatic exclusion of sensitive files from version control
- **Environment Security**: Comprehensive environment variable configuration
- **Input Validation**: Enhanced validation for all user inputs
- **Audit Trail**: Complete logging of security-related operations

### ✅ **Comprehensive Documentation**
- **Deployment Guide**: Complete first-time deployment instructions
- **Troubleshooting**: Common issues and solutions
- **Security Checklist**: Production security recommendations
- **Configuration Reference**: Complete environment variables guide

## 🔐 Authentication & Authorization

### Authentication Methods
1. **Windows Active Directory** (Primary)
   - LDAP-based authentication
   - Supports multiple username formats
   - Automatic user information retrieval

2. **Local Accounts** (Fallback)
   - Built-in accounts for emergency access
   - Configurable via environment variables

### Role-Based Access Control

| Role | Access Level | Capabilities |
|------|-------------|-------------|
| **OSS** | Limited | • View access ports only (Gi/Te based on model)<br>• Basic MAC/port information<br>• Auto-filtered uplinks (Te/Tw/Po ports)<br>• Limited VLAN details for trunk/general ports |
| **NetAdmin** | Full | • View all ports including uplinks<br>• Complete VLAN information<br>• Port configuration details<br>• Full MAC trace capabilities across all switch series |
| **SuperAdmin** | Full | • All NetAdmin capabilities<br>• Administrative functions<br>• Full audit log access<br>• Switch model management capabilities |

## 🌐 Web Interface

### Login Page
- Supports both local and domain authentication
- Clean, professional interface with company branding
- Real-time authentication status

### Main Dashboard
- **Step 1**: Site and Floor Selection
  - Searchable dropdowns with Select2 integration
  - Dynamic switch loading based on selection
- **Step 2**: MAC Address Entry
  - Multiple format support (xx:xx:xx:xx:xx:xx, xx-xx-xx-xx-xx-xx, xxxx.yyyy.zzzz)
  - Real-time tracing with progress indicators

### Results Display
- **Found Results**: Switch, port, VLAN, and configuration details
- **Role-Based Filtering**: Information displayed based on user permissions
- **Error Handling**: Clear messaging for connection issues or failures

### Switch Management Interface (NetAdmin/SuperAdmin Only)
- **CRUD Operations**: Create, read, update, and delete switches, sites, and floors
- **Real-time Search**: Filter switches by name, IP, model, site, or floor
- **Bulk Operations**: Manage multiple switches efficiently
- **Data Validation**: Form validation and error handling
- **Audit Logging**: All management operations are logged for compliance

## 📊 Monitoring & Health Checks

### Health Endpoint
- **URL**: `/health`
- **Purpose**: Container orchestration liveness and readiness probes
- **Response**: JSON with application status, version, and configuration summary
- **Enhanced Validation**: Database connectivity and schema verification

### System Logs
- Application startup and shutdown events
- Switch connection status and errors
- Performance metrics and troubleshooting information
- Database initialization and migration logs

### Audit Logs
- User authentication events with role information
- MAC trace requests with full details
- Role-based access decisions
- Session management activities
- Database operations and schema changes

## 🛡️ Security Features

### Container Security
- Runs as non-root user (UID 1000)
- Read-only root filesystem where possible
- Drops all capabilities
- No privilege escalation

### Authentication Security
- LDAP Simple Authentication with secure credential validation
- Multiple username formats support
- Secure session management with configurable timeout
- Comprehensive failed login protection

### Session Security
- **Environment-Based Configuration**: All session settings configurable via environment variables
- **HTTP/HTTPS Compatibility**: Proper cookie security for different deployment scenarios
- **Security Headers**: HttpOnly, Secure, and SameSite cookie policies
- **Configurable Timeouts**: Adjustable session lifetime for security requirements

### Authorization Security
- Least privilege principle (default OSS role)
- Explicit permissions require specific AD groups
- Role-based information filtering
- Complete audit trail

### Network Security
- SSH key validation and automated host key management
- All switch communication encrypted
- Environment-based credential protection

## 🏗️ Architecture

### Application Components
- **Flask Web Framework**: Lightweight and secure web server
- **Paramiko SSH Client**: Encrypted switch communication
- **LDAP3**: Active Directory integration
- **Role-Based Access Control**: Multi-tier permission system
- **SQLAlchemy ORM**: Database abstraction with automatic initialization

### Deployment Architecture
- **Standalone**: Single Python application
- **Containerized**: Docker with multi-stage builds and health checks
- **Kubernetes**: High availability with load balancing
- **Scalable**: Horizontal scaling support

### Database Architecture
- **Automatic Initialization**: Zero-configuration database setup
- **Schema Management**: Automated table creation and validation
- **Migration Support**: Seamless database version upgrades
- **Health Monitoring**: Built-in connectivity and schema validation

## 📚 Documentation

- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)**: Complete first-time deployment instructions
- **[Architecture Documentation](architecture/README.md)**: System architecture for different teams
- **Configuration Examples**: Sample environment and switch configurations
- **Troubleshooting**: Common issues and solutions
- **API Documentation**: Health check and monitoring endpoints

## 🔄 Upgrade from Previous Versions

### From v2.1.2 and Earlier
1. **Backup your data**: Always backup your database before upgrading
2. **Update environment variables**: Add new session security variables to your `.env` file
3. **Database initialization**: The upgrade will automatically handle database schema updates
4. **Test deployment**: Verify all functionality works in your environment

### Session Configuration Updates
Add these new variables to your `.env` file:
```env
# Session Security Configuration (v2.1.3+)
SESSION_COOKIE_SECURE=false  # Set to 'true' for HTTPS deployments
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
PERMANENT_SESSION_LIFETIME=5
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Crispy-Pasta/SwitchPortManager/issues)
- **Documentation**: Check the docs folder for detailed guides
- **Community**: Discussions and Q&A on GitHub

## 🙏 Acknowledgments

- Dell Technologies for switch platform documentation
- Flask and Python communities for excellent frameworks
- Container and orchestration communities for deployment platforms

---

**Version**: 2.1.3  
**Last Updated**: August 2025  
**Maintainer**: Network Operations Team

## 🔄 Changelog (v2.1.3)

### 🔐 **Deployment & Security Enhancements**
- ✅ **Automatic Database Initialization**: Zero-configuration database setup with automatic schema creation
- ✅ **Enhanced Session Security**: Configurable session cookie settings for HTTP/HTTPS deployments  
- ✅ **Production Health Checks**: Enhanced health monitoring with database connectivity validation
- ✅ **Container Security**: Improved Docker deployment with proper health checks and resource limits
- ✅ **Security Hardening**: Data protection with automatic exclusion of sensitive files
- ✅ **Comprehensive Documentation**: Complete deployment guide with troubleshooting and security best practices

### 🔧 **Technical Improvements**
- ✅ **Database Connection Retry**: Robust database initialization with containerized deployment support
- ✅ **Environment-Based Configuration**: All session and security settings configurable via environment variables
- ✅ **Enhanced Logging**: Detailed startup, initialization, and operation logging
- ✅ **Docker Entrypoint**: Proper containerized startup sequence with database initialization
- ✅ **Production Docker Compose**: Enhanced production deployment configuration with security defaults

### 🛡️ **Security Features (Previous Versions)**
- ✅ **Enhanced Input Validation**: Comprehensive MAC address format validation with security-focused error messages
- ✅ **Command Injection Prevention**: Multi-layer protection against malicious network configuration attempts
- ✅ **VLAN Management Security**: Enterprise-grade input validation for all VLAN management operations
- ✅ **Audit Trail Enhancement**: Complete logging of user actions and security events

### 🎨 **User Experience Improvements (Previous Versions)**
- ✅ **Enhanced VLAN Manager**: Optional VLAN name toggle and combined preview+execute workflow
- ✅ **Improved UI Consistency**: Professional, standardized interface design across all components
- ✅ **Session Management**: Advanced session timeout handling with proactive warnings
- ✅ **Frontend Validation**: Enhanced client-side validation and error handling
