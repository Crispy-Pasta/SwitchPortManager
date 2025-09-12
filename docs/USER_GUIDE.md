# Dell Switch Port Tracer v2.1.3 - User Guide

## 📖 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [User Roles & Permissions](#user-roles--permissions)
- [Getting Started](#getting-started)
- [MAC Address Tracing](#mac-address-tracing)
- [Performance & Limitations](#performance--limitations)
- [Troubleshooting](#troubleshooting)
- [Support](#support)

---

## 🏢 Overview

The Dell Switch Port Tracer v2.1.3 is an enterprise-grade web application designed for network administrators to quickly trace MAC addresses across Dell switches in multi-site environments. The application uses secure SSH connections to switches and provides real-time port identification with detailed configuration information while maintaining security through role-based access control.

### Architecture (v2.1.3)
- **3-Container Docker Stack**: nginx + Flask app + PostgreSQL database
- **SSL/HTTPS**: Secure web access with automatic certificates
- **SSH-based Switch Access**: Secure encrypted connections to Dell switches
- **PostgreSQL Database**: Persistent storage with encrypted credentials
- **Windows AD Integration**: LDAP authentication with corporate directory

### Key Benefits
- **6x Faster Tracing**: SSH concurrent processing reduces search time from 30+ seconds to 5-8 seconds
- **Multi-Site Support**: Manage 27+ sites with 155+ switches simultaneously  
- **Role-Based Security**: OSS, NetAdmin, and SuperAdmin access levels
- **Windows AD Integration**: Seamless authentication with existing infrastructure
- **Real-Time Results**: Live progress updates and detailed port information
- **Production Ready**: SSL/HTTPS, database persistence, automated backups

---

## ⚡ Features

### 🔍 **MAC Address Tracing**
- **Multiple MAC Formats**: Accepts colon, hyphen, and dotted formats
  - `00:1B:63:84:45:E6` (colon-separated)
  - `00-1B-63-84-45-E6` (hyphen-separated)  
  - `001B.6384.45E6` (dotted format)
- **Concurrent Processing**: Searches multiple switches simultaneously
- **Port Configuration Details**: Mode (access/trunk/general), VLANs, descriptions
- **Uplink Filtering**: Automatically excludes uplink ports from OSS user results

### 🏢 **Multi-Site Management**
- **Site Selection**: Dropdown with 27+ configured sites
- **Floor-Based Organization**: Switches organized by building floors
- **Dynamic Loading**: Switches loaded based on site/floor selection
- **Search Integration**: Select2 dropdowns for easy site/floor finding

### 👥 **User Management**
- **Windows AD Integration**: SSO with existing domain accounts
- **Local Accounts**: Fallback authentication for non-domain users
- **Role-Based Access**: Three permission levels with specific capabilities
- **Session Management**: Secure login/logout with audit trails

### 📊 **Monitoring & Auditing**
- **Real-Time Logging**: All user actions logged with timestamps
- **Performance Metrics**: Execution time and worker thread tracking
- **Progress Updates**: Live feedback for large switch batches
- **Audit Trails**: Comprehensive activity logging for compliance

---

## 👥 User Roles & Permissions

### 🔒 **OSS (Operations Support)**
**Target Users**: Level 1 support, contractors, junior staff

**Access Level**: **Limited**
- ✅ View MAC addresses on access ports
- ✅ See basic port information (port number, VLAN)
- ❌ Cannot see uplink ports (hidden for security)
- ❌ Limited VLAN details on trunk/general ports
- ❌ Cannot see full switch configurations

**Use Cases**: Basic troubleshooting, user connection issues

### 🔧 **NetAdmin (Network Administrator)**  
**Target Users**: Network engineers, senior technicians

**Access Level**: **Full Network Access**
- ✅ View all switch ports including uplinks
- ✅ Complete VLAN configuration details
- ✅ Port descriptions and advanced settings
- ✅ Full switch configuration visibility
- ✅ Advanced troubleshooting capabilities

**Use Cases**: Network troubleshooting, VLAN management, infrastructure work

### 👑 **SuperAdmin (Super Administrator)**
**Target Users**: Network architects, senior engineers, managers

**Access Level**: **Complete System Access**
- ✅ All NetAdmin capabilities
- ✅ Full system access and configuration
- ✅ Advanced administrative functions
- ✅ Complete audit trail access
- ✅ System management capabilities

**Use Cases**: System administration, security reviews, advanced troubleshooting

---

## 🚀 Getting Started

### 1. **Access the Application**
Navigate to: `http://your-server:8443` (production) or `http://localhost:5000` (development)

### 2. **Login**
**Windows AD Users**: Use your domain credentials (`username@domain.com`)
**Local Users**: Use assigned local account credentials

### 3. **Select Location**
1. Choose your **Site** from the dropdown (searchable)
2. Select the **Floor** where the target device is located
3. Verify the switches are loaded (green checkmark with switch count)

### 4. **Enter MAC Address**
- Type or paste the MAC address in any supported format
- The system automatically normalizes the format
- Click **"🔍 Trace MAC Address"** to begin

### 5. **Review Results**
- Results appear in real-time as switches are processed
- Green results indicate MAC address found
- Red/orange results indicate issues or restrictions

---

## 🔍 MAC Address Tracing

### **Search Process**
1. **Concurrent Processing**: All floor switches searched simultaneously
2. **Progress Tracking**: Live updates for batches over 5 switches  
3. **Automatic Filtering**: Results filtered based on user role
4. **Detailed Information**: Port configuration and VLAN details provided

### **Result Information**
Each successful result includes:
- **Switch Information**: Name and IP address
- **Port Details**: Physical port number and mode badge
- **Port Description**: Custom description if configured
- **VLAN Information**: MAC VLAN, Port PVID, Allowed VLANs
- **Port Mode**: Access, Trunk, or General configuration

### **Supported Dell Switch Models**
- **N2000 Series**: N2048 and variants
  - Access Ports: `Gi1/0/X` (Gigabit)
  - Uplink Ports: `Te1/0/X` (10-Gigabit)

- **N3000 Series**: N3024P, N3048P and variants  
  - Access Ports: `Gi1/0/X` (Gigabit)
  - Uplink Ports: `Te1/0/X` (10-Gigabit)

- **N3200 Series**: N3248 and variants
  - Access Ports: `Te1/0/X` (10-Gigabit)
  - Uplink Ports: `Tw1/0/X` (20-Gigabit)

---

## ⚡ Performance & Limitations

### **Performance Specifications**
- **Concurrent Workers**: 8 parallel connections per site
- **Search Speed**: 5-8 seconds for 10 switches (vs 30+ seconds sequential)
- **Timeout Protection**: 60-second maximum execution time
- **Batch Size**: Optimized for 1-20 switches per floor

### **Concurrent User Limits**
- **Per Site Limit**: Maximum 10 simultaneous users per site
- **Reason**: Dell switch SSH session limitations (10 concurrent max)
- **Behavior**: Additional users receive "too many users" message
- **Resolution**: Wait 30-60 seconds and retry

### **System Limitations**
- **Dell SSH Constraints**: Limited to 10 concurrent SSH sessions per switch
- **Network Timeout**: 15-second SSH connection timeout per switch
- **Processing Timeout**: 60-second maximum for entire trace operation
- **Role Restrictions**: OSS users cannot see uplink ports or full VLAN configs

### **Best Practices**
- **Peak Hours**: Limit concurrent users during high-traffic periods
- **Large Sites**: Consider splitting large floors across multiple searches
- **Timeout Issues**: Check network connectivity to switches if timeouts occur
- **Performance**: Monitor system logs for performance optimization

---

## 🎨 **User Interface Improvements (v2.2.0)**

### **Professional Select2 Dropdown Enhancements**
- **Smart Visual Design**: Intelligent color differentiation between placeholder text (light gray #9ca3af) and selected values (dark text #2c3e50)
- **Perfect Text Alignment**: Proper vertical centering and consistent spacing across all dropdown elements
- **Optimized Search Experience**: 
  - Search disabled for Workflow Type dropdown (only 2 options - more efficient)
  - Search retained for Target Switch dropdown (searchable for large lists)
- **Cross-Browser Consistency**: Enhanced CSS specificity with JavaScript fallbacks for uniform appearance
- **Real-Time Updates**: Dynamic styling adjustments when selections change, maintaining visual consistency

### **Workflow-Based VLAN Management**
- **Structured Workflows**: Clear distinction between Onboarding (🟢 Enable Ports) and Offboarding (🔴 Shutdown Ports) operations
- **Intuitive Interface**: Simplified workflow selection with visual indicators and contextual help
- **Enhanced User Experience**: Streamlined form with dynamic help text that updates based on selected workflow
- **Professional Styling**: Consistent visual hierarchy with improved spacing and typography

### **Previous UI Improvements (v2.1.1)**
- **Enhanced VLAN Management**: Updated placeholder examples following enterprise standards
- **Switch Management Optimizations**: Dropdown constraints and layout fixes
- **Enhanced CSS**: Stronger specificity rules to override global styles
- **Runtime Consistency**: JavaScript enforcement for width consistency

---

## 🔧 Troubleshooting

### **Common Issues**

#### **"Too Many Concurrent Users"**
- **Cause**: Site has reached 10 concurrent user limit
- **Solution**: Wait 30-60 seconds and try again
- **Prevention**: Coordinate with team during peak usage

#### **"Connection Failed" for Switches**
- **Cause**: Network connectivity issues or switch maintenance
- **Solution**: Check switch availability and network path
- **Escalation**: Contact network team if persistent

#### **"Dropdown Width Issues" (Switch Management)**
- **Cause**: Browser caching old CSS styles or conflicting global styles
- **Solution**: Hard refresh browser (Ctrl+F5) or clear cache
- **Status**: Fixed in v2.1.1 with enhanced CSS specificity

#### **"MAC Address Not Found"**
- **Possible Causes**:
  - Device not connected to selected floor
  - MAC address aged out of switch table
  - Device on different site/floor
  - OSS user viewing uplink-connected device
- **Solutions**:
  - Verify device is actively connected
  - Try different floors/sites
  - Check with NetAdmin if OSS user

#### **Slow Performance**
- **Causes**: Network latency, switch overload, high concurrent usage
- **Solutions**: 
  - Retry during off-peak hours
  - Check network connectivity
  - Contact system administrator

### **Error Messages**

| Error | Meaning | Action |
|-------|---------|--------|
| "Not authenticated" | Session expired | Re-login to application |
| "No switches found" | Invalid site/floor | Verify site/floor selection |
| "Trace operation timed out" | Network/performance issue | Retry or contact support |
| "Failed to connect to switch" | Switch unreachable | Check switch status |
| "System error during trace" | Application error | Contact system administrator |

### **Performance Monitoring**
- **System Logs**: `port_tracer.log` for system events
- **Audit Logs**: `audit.log` for user activity tracking
- **Real-Time Metrics**: Execution time displayed in logs
- **Worker Utilization**: Thread pool usage tracked

---

## 📞 Support

### **Self-Service Resources**
- **User Guide**: This document
- **System Status**: Check `/health` endpoint
- **Logs**: System administrators can review application logs

### **Contact Information**
- **Level 1 Support**: Network Operations Center (NOC)
- **Level 2 Support**: Network Engineering Team  
- **System Issues**: DevOps/Infrastructure Team
- **Feature Requests**: Network Architecture Team

### **Escalation Path**
1. **User Issues**: Contact NOC for basic troubleshooting
2. **Network Issues**: Escalate to Network Engineering
3. **System Issues**: Escalate to DevOps team
4. **Security Issues**: Contact Information Security team

### **Documentation**
- **User Guide**: This document (USER_GUIDE.md)
- **Deployment Guide**: DEPLOYMENT.md
- **DevOps Guide**: DEVOPS_GUIDE.md
- **API Documentation**: Available at `/health` endpoint

---

## 📊 Appendix

### **Supported MAC Address Formats**
```
Colon-separated:    00:1B:63:84:45:E6
Hyphen-separated:   00-1B-63-84-45-E6  
Dotted (Dell):      001B.6384.45E6
```

### **Site Coverage**
- **Total Sites**: 27 configured locations
- **Total Switches**: 155+ Dell switches
- **Switch Models**: N2048, N3024P, N3248, and variants
- **Geographic Coverage**: Multi-building enterprise deployment

### **Version Information**
- **Application Version**: 1.0.2
- **Last Updated**: July 2025
- **Repository**: https://github.com/Crispy-Pasta/DellPortTracer
- **License**: MIT License

---

*This guide is updated regularly. For the latest version, check the repository documentation.*
