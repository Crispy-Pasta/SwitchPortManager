# Dell Switch Port Tracer v2.0

## 🚀 **Enterprise-Grade MAC Address Tracing Solution**

A secure, scalable web application for tracing MAC addresses across Dell switches in enterprise environments with advanced monitoring, protection, and logging capabilities.

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)

## 🚀 Features

- **Multi-Site Management**: Support for multiple sites and floors with centralized switch inventory
- **Database-Driven Architecture**: SQLite database for scalable switch inventory management
- **Switch Management UI**: Web-based CRUD interface for network administrators to manage switches, sites, and floors
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

### Option 1: Standard Python Deployment

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Crispy-Pasta/DellPortTracer.git
   cd DellPortTracer
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**
   Create a `.env` file:
   ```env
   # Dell Switch SSH Credentials
   SWITCH_USERNAME=your_switch_username
   SWITCH_PASSWORD=your_switch_password

   # Web Service Configuration
   OSS_PASSWORD=oss123
   NETADMIN_PASSWORD=netadmin123
   SUPERADMIN_PASSWORD=superadmin123

   # Windows Active Directory Configuration (Optional)
   USE_WINDOWS_AUTH=true
   AD_SERVER=ldap://your-domain.com
   AD_DOMAIN=your-domain.com
   AD_BASE_DN=DC=your-domain,DC=com
   ```

4. **Initialize Database**
   ```bash
   # If migrating from switches.json (existing installations)
   python migrate.py
   
   # For new installations, the database will be created automatically
   ```

5. **Start the Application**
   ```bash
   python port_tracer_web.py
   ```

### Option 2: Docker Deployment

1. **Build and Run with Docker Compose**
   ```bash
   git clone https://github.com/Crispy-Pasta/DellPortTracer.git
   cd DellPortTracer
   docker-compose up -d
   ```

2. **Access the Application**
   - Open http://localhost:5000

### Option 3: Kubernetes Deployment

1. **Deploy to Kubernetes**
   ```bash
   git clone https://github.com/Crispy-Pasta/DellPortTracer.git
   cd DellPortTracer
   
   # For Windows
   .\deploy.ps1 deploy
   
   # For Linux/Mac
   chmod +x deploy.sh
   ./deploy.sh deploy
   ```

2. **Access Methods**
   - **NodePort**: `http://<node-ip>:30080`
   - **Port Forward**: `kubectl port-forward service/dell-port-tracer-service 8080:80`
   - **Ingress**: Configure DNS for production access

For detailed Kubernetes deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

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

### Switch Management Interface (NetAdmin/SuperAdmin Only)
- **CRUD Operations**: Create, read, update, and delete switches, sites, and floors
- **Real-time Search**: Filter switches by name, IP, model, site, or floor
- **Bulk Operations**: Manage multiple switches efficiently
- **Data Validation**: Form validation and error handling
- **Audit Logging**: All management operations are logged for compliance

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
