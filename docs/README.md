# Dell Switch Port Tracer v2.1.3

## 🚀 **Enterprise-Grade MAC Address Tracing Solution**

A secure, production-ready web application for tracing MAC addresses across Dell switches with advanced monitoring, SSL/HTTPS support, and automated deployment capabilities.

![Version](https://img.shields.io/badge/version-2.1.3-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Docker%20%7C%20Linux-lightgrey)
![Status](https://img.shields.io/badge/status-Production%20Ready-green)

## 🚀 Features

- **Multi-Site Management**: Support for multiple sites and floors with centralized switch inventory
- **Windows AD Integration**: Secure LDAP authentication with role-based access control  
- **Role-Based Permissions**: Three access levels (OSS, NetAdmin, SuperAdmin) with different capabilities
- **Dell Switch Support**: Comprehensive support for Dell N2000, N3000, and N3200 series switches (including N2048, N3248, N3024P models)
- **Intelligent Filtering**: Automatic uplink port detection and VLAN information filtering
- **Comprehensive Audit Logging**: Full activity tracking for security and compliance
- **Responsive Web Interface**: Clean, modern UI with real-time MAC address tracing
- **Port Configuration Details**: Detailed port mode, VLAN, and description information
- **Container Ready**: Docker and Kubernetes deployment support
- **Production Ready**: Health checks, monitoring, and high availability

## 📋 Requirements

### System Requirements
- Python 3.8+
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

## 🔧 Installation

### Recommended: Production Docker Deployment

**Complete 3-container architecture with SSL/HTTPS support**

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Crispy-Pasta/SwitchPortManager.git
   cd SwitchPortManager
   ```

2. **Configure Environment**
   Copy the template and configure your environment:
   ```bash
   cp config/.env.template .env
   # Edit .env with your specific values
   ```

   Required variables in `.env`:
   ```env
   # Application Security
   SECRET_KEY=your_secure_secret_key_here
   
   # Dell Switch SSH Credentials
   SWITCH_USERNAME=your_switch_username
   SWITCH_PASSWORD=your_switch_password

   # Database Configuration (auto-configured)
   DATABASE_URL=postgresql://porttracer_user:porttracer_pass@postgres:5432/port_tracer_db
   
   # User Authentication
   ADMIN_PASSWORD=your_admin_password
   OSS_PASSWORD=your_oss_password
   NETADMIN_PASSWORD=your_netadmin_password
   SUPERADMIN_PASSWORD=your_superadmin_password

   # Windows Active Directory (Optional)
   USE_WINDOWS_AUTH=true
   AD_SERVER=10.20.100.15
   AD_DOMAIN=your-domain.com
   AD_BASE_DN=DC=your-domain,DC=com
   ```

3. **Deploy with Safe Script**
   ```bash
   # Automated deployment with backup and rollback protection
   ./deploy-safe.sh
   ```

4. **Access the Application**
   - **HTTPS**: `https://your-server-ip/` (SSL enabled)
   - **HTTP**: `http://your-server-ip/` (also available)
   - **Custom Domain**: Configure DNS for `https://kmc-port-tracer/`

### Architecture Components

**3-Container Production Setup:**
- **dell-port-tracer-app**: Flask application (Python)
- **dell-port-tracer-nginx**: Reverse proxy with SSL/HTTPS
- **dell-port-tracer-postgres**: Database with persistent storage

**Features:**
- ✅ **SSL/HTTPS enabled** with automatic certificate generation
- ✅ **Database persistence** with named volumes and backups
- ✅ **Safe deployment** with automatic backup and rollback
- ✅ **Health monitoring** for all containers
- ✅ **Production logging** and audit trails

### Alternative: Development Setup

**For development or testing purposes:**

1. **Python Direct Deployment**
   ```bash
   git clone https://github.com/Crispy-Pasta/SwitchPortManager.git
   cd SwitchPortManager/app
   pip install -r requirements.txt
   
   # Configure environment
   cp ../.env.example .env
   # Edit .env with your settings
   
   python port_tracer_web.py
   ```

2. **Development Docker Compose**
   ```bash
   # Basic 2-container setup without SSL
   docker-compose -f docker-compose.yml up -d
   ```

### Manual Docker Deployment

**If you prefer manual control:**

```bash
# 1. Start database
docker run -d --name dell-port-tracer-postgres \
  -e POSTGRES_DB=port_tracer_db \
  -e POSTGRES_USER=porttracer_user \
  -e POSTGRES_PASSWORD=porttracer_pass \
  -v dell_port_tracer_postgres_data:/var/lib/postgresql/data \
  postgres:15-alpine

# 2. Build and start application
docker build -t dell-port-tracer-app ./app
docker run -d --name dell-port-tracer-app \
  --env-file .env \
  --link dell-port-tracer-postgres:postgres \
  dell-port-tracer-app

# 3. Start nginx proxy
docker run -d --name dell-port-tracer-nginx \
  -p 80:80 -p 443:443 \
  -v ./nginx.conf:/etc/nginx/nginx.conf:ro \
  --link dell-port-tracer-app:app \
  nginx:alpine
```

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

### Active Directory Group Mapping
- **Default Role**: OSS (least privilege)
- **SOLARWINDS_OSS_SD_ACCESS** → OSS
- **NOC TEAM** → NetAdmin  
- **Groups containing ADMIN/SUPERADMIN** → SuperAdmin

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

## 📊 Monitoring & Health Checks

### Health Endpoint
- **URL**: `/health`
- **Purpose**: Kubernetes liveness and readiness probes
- **Response**: JSON with application status, version, and configuration summary

### System Logs
- Application startup and shutdown events
- Switch connection status and errors
- Performance metrics and troubleshooting information

### Audit Logs
- User authentication events with role information
- MAC trace requests with full details
- Role-based access decisions
- Session management activities

### Log Format
```
2025-07-24 10:30:15,123 - AUDIT - User: jdoe (netadmin) - LOGIN SUCCESS via windows_ad
2025-07-24 10:30:45,456 - AUDIT - User: jdoe - TRACE REQUEST - Site: MAIN, Floor: 2, MAC: 00:11:22:33:44:55
2025-07-24 10:30:47,789 - AUDIT - User: jdoe - MAC FOUND - 00:11:22:33:44:55 on SW-02 port Gi1/0/24 [Mode: access]
```

## 🔍 MAC Address Tracing

### Supported Formats
- **Colon-separated**: `00:1B:63:84:45:E6`
- **Hyphen-separated**: `00-1B-63-84-45-E6`
- **Dot-separated**: `001B.6384.45E6`

### Process Flow
1. **Site/Floor Selection**: User selects target location
2. **Switch Loading**: Application loads relevant switches from inventory
3. **MAC Lookup**: Parallel SSH connections to all switches in scope
4. **Result Processing**: Parse MAC table output and gather port details
5. **Role-Based Filtering**: Apply permissions and display results

### Dell Switch Commands
- **MAC Table Lookup**: `show mac address-table address XX:XX:XX:XX:XX:XX`
- **Port Configuration**: Supports all Dell port types:
  - **N2000/N3000 Series**: `show running-config interface GiX/X/X` (access), `TeX/X/X` (uplink)
  - **N3200 Series**: `show running-config interface TeX/X/X` (access), `TwX/X/X` (uplink)
- **Connection Management**: Automated SSH session handling with model-aware commands

## 🛡️ Security Features

### Container Security
- Runs as non-root user (UID 1000)
- Read-only root filesystem where possible
- Drops all capabilities
- No privilege escalation

### Authentication Security
- LDAP Simple Authentication with secure credential validation
- Multiple username formats support
- Secure session management with timeout
- Comprehensive failed login protection

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

### Deployment Architecture
- **Standalone**: Single Python application
- **Containerized**: Docker with multi-stage builds
- **Kubernetes**: High availability with load balancing
- **Scalable**: Horizontal scaling support

## 📚 Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)**: Complete Kubernetes deployment guide
- **Configuration Examples**: Sample environment and switch configurations
- **Troubleshooting**: Common issues and solutions
- **API Documentation**: Health check and monitoring endpoints

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Crispy-Pasta/DellPortTracer/issues)
- **Documentation**: Check the docs folder for detailed guides
- **Community**: Discussions and Q&A on GitHub

## 🙏 Acknowledgments

- Dell Technologies for switch platform documentation
- Flask and Python communities for excellent frameworks
- Kubernetes community for container orchestration platform

---

**Version**: 1.0.0  
**Last Updated**: July 2025  
**Maintainer**: Network Operations Team
