# Switch Port Manager v2.1.5

> **Note:** Repository migrated from `DellPortTracer` to `SwitchPortManager` for better organization and expanded functionality.

## 🚀 **Enterprise-Grade MAC Address Tracing Solution**

A secure, scalable web application for tracing MAC addresses across Dell switches in enterprise environments with advanced monitoring, protection, and logging capabilities. Enhanced security features including input validation and sanitized error messages.

![Version](https://img.shields.io/badge/version-2.1.5-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey)
![Security](https://img.shields.io/badge/security-enhanced-green)

## 🚀 Features

### 🔐 Security Features
- **Enhanced Input Validation**: Comprehensive MAC address format validation with security-focused error messages
- **Sanitized Error Responses**: Error messages exclude potentially harmful examples or security-sensitive information
- **Command Injection Prevention**: Robust input sanitization to prevent malicious command execution
- **Role-Based Access Control**: Three security levels with least-privilege access patterns

### 🏢 Enterprise Management
- **Multi-Site Management**: Support for multiple sites and floors with centralized switch inventory
- **Comprehensive Management Interface**: Tabbed interface for managing Sites, Floors, and Switches with full CRUD operations
- **Site & Floor Administration**: Create, edit, and delete sites and floors with proper hierarchical relationships
- **Database-Driven Architecture**: PostgreSQL database for enterprise-grade scalability and reliability
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
- **Container Ready**: Docker and Kubernetes deployment support
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

## 🔧 Installation

### Option 1: Standard Python Deployment

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

   # Web Service Configuration
   OSS_PASSWORD=oss123
   NETADMIN_PASSWORD=netadmin123
   SUPERADMIN_PASSWORD=superadmin123
   WEB_PASSWORD=admin_password_here

   # CPU Safety Thresholds
   CPU_GREEN_THRESHOLD=20
   CPU_YELLOW_THRESHOLD=40
   CPU_RED_THRESHOLD=60

   # Switch Protection Monitor Configuration
   MAX_CONNECTIONS_PER_SWITCH=8
   MAX_TOTAL_CONNECTIONS=64
   COMMANDS_PER_SECOND_LIMIT=10

   # Syslog Configuration (Optional)
   SYSLOG_ENABLED=true
   SYSLOG_SERVER=your-syslog-server
   SYSLOG_PORT=514

   # Windows Active Directory Configuration (Optional)
   USE_WINDOWS_AUTH=false
   AD_SERVER=ldap://your-domain.com
   AD_DOMAIN=your-domain.com
   AD_BASE_DN=DC=your-domain,DC=com
   ```

4. **Setup PostgreSQL Database**
   
   **Option A: Using Docker (Recommended)**
   ```bash
   # Run PostgreSQL in Docker
   docker run -d --name port-tracer-postgres \
     -e POSTGRES_DB=port_tracer_db \
     -e POSTGRES_USER=dell_tracer_user \
     -e POSTGRES_PASSWORD=secure_password_here \
     -p 5432:5432 postgres:15
   ```
   
   **Option B: Using Existing PostgreSQL Server**
   ```sql
   -- Connect to your PostgreSQL server and run:
   CREATE DATABASE port_tracer_db;
   CREATE USER dell_tracer_user WITH PASSWORD 'secure_password_here';
   GRANT ALL PRIVILEGES ON DATABASE port_tracer_db TO dell_tracer_user;
   ```

5. **Initialize Database Schema and Data**
   ```bash
   # Initialize database with schema and sample data
   python init_database.py
   
   # If migrating from SQLite (existing installations)
   python migrate_data.py
   ```

5. **Start the Application**
   ```bash
   python port_tracer_web.py
   ```

### Option 2: Docker Deployment

1. **Build and Run with Docker Compose**
   ```bash
   git clone https://github.com/Crispy-Pasta/SwitchPortManager.git
   cd SwitchPortManager
   docker-compose up -d
   ```

2. **Access the Application**
   - Open http://localhost:5000

### Option 3: Kubernetes Deployment

1. **Deploy to Kubernetes**
   ```bash
   git clone https://github.com/Crispy-Pasta/SwitchPortManager.git
   cd SwitchPortManager
   
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
- **Continuous format**: `001B638445E6`

### Security Enhancements
- **Input Validation**: Strict MAC address format validation using regex patterns
- **Error Message Sanitization**: Security-focused error responses that provide helpful guidance without exposing sensitive information
- **No Malicious Examples**: Error messages exclude potentially harmful input examples
- **Audit Trail**: All invalid input attempts are logged for security monitoring

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

**Version**: 2.1.5  
**Last Updated**: August 2025
**Maintainer**: Network Operations Team

## 🔄 Changelog (v2.1.5)

### 🔐 Session Timeout & Security Enhancements
- ✅ **Enhanced Session Management**: Improved user experience with proactive session timeout handling
  - Fixed timezone-aware datetime handling to prevent session expiration errors
  - Configurable 5-minute session timeout with proper inactivity tracking
  - Session state consistency across multiple browser tabs and page navigation
  - Graceful session expiration with clear user notification and redirect
- ✅ **Session Timeout Warning System**: JavaScript-based user-friendly timeout notifications
  - Proactive 1-minute warning before session expires with countdown timer
  - "Stay Logged In" functionality to extend sessions without losing work
  - Full-screen logout overlay with progress bar for clear user feedback
  - Toast notifications for session state changes and keep-alive confirmations
- ✅ **New Session Management API Endpoints**: Backend support for enhanced session handling
  - `/api/session/keepalive` - Extends session timeout when user chooses to stay logged in
  - `/api/session/check` - Validates session status for consistent state management
  - Comprehensive audit logging for all session management activities
  - Enhanced error handling and graceful fallback for session-related operations
- ✅ **Cross-Tab Session State Management**: Consistent session handling across browser instances
  - Periodic session validation (every 2 minutes) to detect stale sessions
  - Browser tab visibility detection for smart session checking
  - Automatic session cleanup and user notification on expiration
  - Prevention of stale session operations that could cause confusion

### 🛡️ Security & Stability Improvements
- ✅ **Robust Session State Validation**: Enhanced security through consistent session checking
- ✅ **Improved Error Handling**: Better user experience during session timeouts and network issues
- ✅ **Audit Trail Enhancement**: Complete logging of session management events for compliance
- ✅ **Frontend State Management**: Smart JavaScript session tracking with graceful degradation

## 🔄 Changelog (v2.1.3)

### 🎨 Enhanced VLAN Manager User Experience
- ✅ **Optional VLAN Name Toggle**: Added "Keep Existing VLAN Name" option for flexibility
  - Users can now preserve existing VLAN names on switches without requiring name input
  - Conditional form validation - VLAN name field becomes optional when toggle is enabled
  - Backend validation respects the toggle state for improved workflow efficiency
- ✅ **Combined Preview+Execute Workflow**: Streamlined VLAN change process
  - Single "Review and Execute Changes" button replaces separate preview and execute actions
  - Always shows preview/review before execution for enhanced safety
  - Execute button integrated directly into preview modal for smoother workflow
- ✅ **Enhanced UI Styling and Consistency**: Professional, standardized interface design
  - Fixed double warning emoji issue in confirmation dialogs
  - Consistent styling across all VLAN management prompts and modals
  - Color-coded status indicators with proper visual hierarchy
  - Improved modal layouts with better spacing and typography
- ✅ **Mutually Exclusive Safety Options**: Enhanced form validation
  - "Force Change" and "Skip Non-Access" options are now mutually exclusive
  - Frontend and backend validation prevents conflicting safety configurations
  - Clear user guidance on option functionality and implications

### 🛡️ VLAN Manager Security Enhancements (v2.1.2)
- ✅ **Comprehensive Input Validation**: Added enterprise-grade input validation for all VLAN management operations
  - Port format validation with strict regex patterns (e.g., Gi1/0/1-48, Te1/0/1-2)
  - VLAN ID validation ensuring IEEE 802.1Q compliance (1-4094)
  - VLAN name validation with Dell switch naming convention compliance
  - Port description validation preventing command injection attacks
- ✅ **Security-Focused Error Messages**: Structured error responses with detailed format requirements
- ✅ **Audit Trail Enhancement**: All invalid input attempts logged with user identification
- ✅ **Command Injection Prevention**: Multi-layer protection against malicious network configuration attempts

### 🔧 Frontend Data Processing Fixes (v2.1.2)
- ✅ **Switch Form Checkbox Handling**: Fixed client-side form processing to properly convert HTML checkbox values
  - Converts checkbox 'on'/undefined values to boolean true/false before API submission
  - Prevents backend validation errors for the 'enabled' field in switch management
  - Ensures proper API compatibility for switch update operations
  - Added comprehensive code comments documenting the fix for maintainability

### 🔧 VLAN Management Features
- ✅ **Advanced VLAN Manager Interface**: Complete VLAN configuration and port management system
- ✅ **Port Range Support**: Handles complex port specifications (ranges, lists, mixed formats)
- ✅ **Uplink Protection**: Automatic detection and protection of critical uplink ports
- ✅ **Switch Model Awareness**: Dell N2000/N3000/N3200 series-specific port handling
- ✅ **Real-time Port Status**: Live port configuration and status checking
- ✅ **VLAN Existence Verification**: Pre-deployment VLAN validation

### 🔐 MAC Address Tracing Security
- ✅ Enhanced MAC address input validation with comprehensive format checking
- ✅ Sanitized error messages that exclude potentially malicious examples
- ✅ Security-focused error responses that provide guidance without exposing sensitive information
- ✅ Improved audit logging for invalid input attempts

### 🎨 Frontend Enhancements
- ✅ Updated JavaScript error handling to align with secure backend responses
- ✅ Removed display of incorrect examples in MAC format error messages
- ✅ Enhanced user experience with clean, helpful error guidance
- ✅ Modern VLAN Manager UI with real-time validation feedback

### 📊 Code Quality & Architecture
- ✅ Modular VLAN management architecture with dedicated security layer
- ✅ Updated documentation and code comments for security components
- ✅ Improved function documentation for all validation functions
- ✅ Enhanced error handling consistency across the application
- ✅ Comprehensive unit test coverage for validation functions
#   =؀�  P r o d u c t i o n   C I / C D   P i p e l i n e   A c t i v e   -   A u t o m a t e d   D e p l o y m e n t   S y s t e m  
 