# Dell Switch Port Tracer v2.0 - NetAdmin Team Guide

## 🎯 **NetAdmin Team Overview**

As a **Network Administrator (NetAdmin)** team member, you have **full access** to all Dell Switch Port Tracer features for comprehensive network management and troubleshooting.

![NetAdmin Role](https://img.shields.io/badge/Role-NetAdmin-blue)
![Access Level](https://img.shields.io/badge/Access-Full-green)

---

## 🔐 **Your Access Level & Permissions**

### ✅ **Full Access Capabilities:**
- **Complete MAC Tracing**: View ALL ports including access, trunk, and uplink ports
- **All Port Types**: Access GigabitEthernet, TenGigabitEthernet, TwentyFiveGigE, and Port-channel interfaces
- **Advanced VLAN Info**: Complete VLAN configuration including trunk allowlists
- **Port Configuration**: Detailed port mode, speed, duplex, and security settings
- **Switch Management**: Full visibility into switch configurations and status
- **All Sites & Floors**: Access to entire network infrastructure
- **Advanced Troubleshooting**: Complete network topology and connection details

### 🔧 **NetAdmin-Specific Features:**
- **Uplink Visibility**: See trunk ports connecting switches (Te, Tw, Po ports)
- **VLAN Trunk Details**: View allowed VLANs on trunk ports
- **Port Security**: Access port security configurations and MAC limits
- **Network Topology**: Understand complete switch interconnections

---

## 🏗️ **Application Architecture (NetAdmin View)**

```
Dell Switch Port Tracer v2.0 Architecture
│
├── 🌐 Web Interface Layer
│   ├── Flask Web Framework (port 5000)
│   ├── Role-Based Access Control (RBAC)
│   ├── Windows AD Integration (LDAP3)
│   └── Session Management & Security
│
├── 🔍 MAC Tracing Engine
│   ├── Parallel SSH Connections (Paramiko)
│   ├── Dell Switch Command Processing
│   ├── MAC Table Parsing & Analysis
│   └── Result Filtering by Role
│
├── 🛡️ Enterprise Protection (v2.0)
│   ├── CPU Safety Monitor
│   │   ├── Configurable CPU thresholds
│   │   ├── Per-switch monitoring
│   │   └── Automatic connection limiting
│   ├── Switch Protection Monitor
│   │   ├── Connection rate limiting
│   │   ├── Concurrent connection limits
│   │   └── Switch health monitoring
│   └── Syslog Integration
│       ├── Centralized logging
│       ├── Structured log format
│       └── Enterprise SIEM integration
│
├── 📊 Network Device Management
│   ├── Switch Inventory (switches.json)
│   ├── Multi-Site Support
│   ├── Dell Model Detection
│   │   ├── N2000 Series (N2048)
│   │   ├── N3000 Series (N3024P, N3248)
│   │   └── N3200 Series (N3248, advanced models)
│   └── Automatic Port Categorization
│
└── 🔐 Security & Audit
    ├── Comprehensive Audit Logging
    ├── Role-Based Information Filtering
    ├── Secure SSH Key Management
    └── Enterprise Authentication
```

---

## 🌐 **Advanced Web Interface Usage**

### **Enhanced Login Options:**
```
Authentication Methods:
├── Windows Active Directory (Primary)
│   ├── domain\username format
│   ├── username@domain.com format
│   └── Automatic role assignment
└── Local Accounts (Fallback)
    ├── netadmin account
    └── Emergency access capability
```

### **Complete Site Management:**
```
🏢 Multi-Site Architecture
├── Site Configuration
│   ├── Site-specific switch inventory
│   ├── Floor-based organization
│   └── Location-aware MAC tracing
├── Switch Models Supported
│   ├── Dell N2000 Series
│   │   ├── GigE access ports (Gi1/0/1-48)
│   │   └── 10GE uplinks (Te1/0/1-4)
│   ├── Dell N3000 Series  
│   │   ├── GigE access ports (Gi1/0/1-24)
│   │   └── 10GE uplinks (Te1/0/1-4)
│   └── Dell N3200 Series
│       ├── 10GE access ports (Te1/0/1-48)
│       └── 25GE uplinks (Tw1/0/1-6)
└── Dynamic Port Detection
    ├── Model-aware port categorization
    ├── Automatic uplink identification
    └── Access port filtering for OSS users
```

---

## 🔍 **Advanced MAC Tracing Features**

### **Complete Port Information:**
| Port Type | NetAdmin View | OSS View | Description |
|-----------|---------------|----------|-------------|
| **GigabitEthernet** | ✅ Full Details | ✅ Basic Info | 1Gb access ports |
| **TenGigabitEthernet** | ✅ Full Details | ✅ Basic Info (Access Only) | 10Gb ports |
| **TwentyFiveGigE** | ✅ Full Details | ❌ Hidden | 25Gb uplink ports |
| **Port-channel** | ✅ Full Details | ❌ Hidden | Link aggregation |
| **Trunk Ports** | ✅ Full Details | ❌ Hidden | Inter-switch links |

### **Advanced Results Analysis:**
```
NetAdmin Result Example:
├── Switch: SW-MAIN-02 (Dell N3248)
├── Port: Te1/0/25 (Uplink to SW-DIST-01)
├── Mode: trunk
├── VLANs: 1,10,20,100-200,300
├── Speed: 10000
├── Duplex: full
├── Port Security: enabled (max 50 MACs)
└── Description: "Uplink to Distribution Switch"
```

### **Dell Switch Command Reference:**
```bash
# MAC Address Lookup
show mac address-table address XX:XX:XX:XX:XX:XX

# Port Configuration (Model-Aware)
# N2000/N3000 Series:
show running-config interface GiX/X/X
show running-config interface TeX/X/X

# N3200 Series:
show running-config interface TeX/X/X  
show running-config interface TwX/X/X

# VLAN Information
show vlan brief
show interfaces switchport

# Port Status
show interfaces status
show interfaces description
```

---

## 🛡️ **Enterprise Protection Features (v2.0)**

### **CPU Safety Monitoring:**
```python
# Configuration in .env
CPU_MONITOR_ENABLED=true
CPU_THRESHOLD_WARNING=70    # Warning at 70% CPU
CPU_THRESHOLD_CRITICAL=85   # Critical at 85% CPU
CPU_CHECK_INTERVAL=30       # Check every 30 seconds
CPU_HISTORY_SIZE=100        # Keep 100 measurements

# Monitoring Behavior:
├── Per-switch CPU monitoring
├── Automatic connection throttling
├── Critical threshold enforcement
└── Detailed logging and alerts
```

### **Switch Protection Monitoring:**
```python
# Configuration in .env  
SWITCH_PROTECTION_ENABLED=true
MAX_CONCURRENT_CONNECTIONS=5    # Max simultaneous connections
CONNECTION_RATE_LIMIT=10        # Max 10 connections per minute
CONNECTION_TIMEOUT=30           # 30 second SSH timeout
RETRY_ATTEMPTS=3               # Retry failed connections 3 times

# Protection Features:
├── Rate limiting prevents switch overload
├── Connection pooling for efficiency  
├── Automatic retry with backoff
└── Switch health status tracking
```

### **Syslog Integration:**
```python
# Configuration in .env
SYSLOG_ENABLED=true
SYSLOG_SERVER=syslog.company.com
SYSLOG_PORT=514
SYSLOG_FACILITY=local0
SYSLOG_LEVEL=info

# Log Categories:
├── Authentication events
├── MAC trace activities  
├── System performance metrics
├── Switch connection status
└── Error and warning conditions
```

---

## 🔧 **Network Administration Tasks**

### **1. Network Troubleshooting:**
```
Issue: "User reports intermittent connectivity"
NetAdmin Process:
1. Trace user's MAC address
2. Check if MAC appears on multiple switches (MAC flapping)
3. Examine uplink ports and trunk configurations
4. Verify VLAN consistency across switches
5. Check port security settings and MAC limits
6. Review switch CPU and performance metrics
```

### **2. Network Changes & Moves:**
```
Task: "Configure new VLAN for department"
NetAdmin Process:
1. Use Port Tracer to identify affected switches
2. Verify current VLAN assignments
3. Plan VLAN implementation across trunk ports
4. Test connectivity with MAC tracing
5. Document changes in switch inventory
```

### **3. Security Investigations:**
```
Task: "Investigate unauthorized device on network"
NetAdmin Process:
1. Trace suspicious MAC address
2. Identify exact switch and port location
3. Review port security configuration
4. Check if device is on appropriate VLAN
5. Coordinate with security team for device investigation
6. Review audit logs for device activity history
```

### **4. Performance Monitoring:**
```
Task: "Monitor network performance during peak hours"
NetAdmin Process:
1. Use CPU safety monitoring to track switch performance
2. Monitor connection rates and switch health
3. Review syslog entries for performance alerts
4. Identify switches approaching resource limits
5. Plan capacity upgrades based on monitoring data
```

---

## 📊 **Switch Inventory Management**

### **switches.json Structure:**
```json
{
  "sites": {
    "MAIN": {
      "name": "Main Building",
      "floors": {
        "1": {
          "name": "Ground Floor",
          "switches": [
            {
              "name": "SW-MAIN-01",
              "ip": "10.1.1.10",
              "model": "N3248",
              "location": "Room 101 - Network Closet",
              "mgmt_vlan": 10,
              "uplink_ports": ["Te1/0/49", "Te1/0/50"],
              "access_ports": "Te1/0/1-48"
            }
          ]
        }
      }
    }
  }
}
```

### **Adding New Switches:**
1. **Physical Installation**: Complete switch physical setup
2. **Network Configuration**: Configure management IP and SSH access
3. **Update Inventory**: Add switch to appropriate site/floor in switches.json
4. **Test Connectivity**: Verify SSH access from Port Tracer
5. **Validate Model Detection**: Confirm automatic port categorization
6. **Document Changes**: Update network documentation

---

## 📈 **Monitoring & Maintenance**

### **Health Check Endpoint:**
```
URL: http://your-server:5000/health
Response Example:
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2025-01-27T10:30:15Z",
  "features": {
    "cpu_monitoring": true,
    "switch_protection": true,
    "syslog_integration": true,
    "windows_auth": true
  },
  "statistics": {
    "total_switches": 24,
    "active_connections": 2,
    "cpu_monitoring_active": true
  }
}
```

### **Log Monitoring:**
```bash
# Application Logs
tail -f port_tracer.log

# Key Log Patterns:
- "AUDIT - User: username - LOGIN SUCCESS"
- "AUDIT - User: username - TRACE REQUEST"  
- "CPU - Switch: SW-01 - CPU: 75% (WARNING)"
- "PROTECTION - Connection rate limit exceeded"
- "SYSLOG - Event sent to syslog server"
```

### **Performance Monitoring:**
```python
# Monitor switch performance
CPU Thresholds:
├── Normal: 0-60% (Green)
├── Warning: 61-84% (Yellow) 
└── Critical: 85%+ (Red - connections limited)

Connection Limits:
├── Concurrent: Max 5 per switch
├── Rate: Max 10 per minute per switch
└── Timeout: 30 seconds per connection
```

---

## 🚨 **Advanced Troubleshooting**

### **Common NetAdmin Issues:**

**1. Switch Not Responding:**
```
Troubleshooting Steps:
├── Check switch IP and SSH connectivity
├── Verify management VLAN configuration
├── Review switch CPU monitoring logs
├── Check switch protection status
└── Test manual SSH connection
```

**2. Incomplete MAC Results:**
```
Possible Causes:
├── Switch model not properly detected
├── Port categorization incorrect
├── SSH timeout during large MAC table query
├── Switch CPU overload protection active
└── VLAN filtering preventing access
```

**3. Performance Issues:**
```
Monitoring Actions:
├── Review CPU safety monitor alerts
├── Check switch protection connection limits
├── Monitor syslog for performance warnings
├── Verify network latency to switches
└── Check for MAC table size limitations
```

### **Advanced Configuration:**

**1. Custom Switch Models:**
```python
# Add support for new Dell models
# Update model detection logic in port_tracer_web.py
DELL_MODELS = {
    'N4000': {
        'access_ports': 'Te1/0/1-48',
        'uplink_ports': 'Fo1/0/1-4',
        'port_prefix': 'Te'
    }
}
```

**2. Environment Customization:**
```bash
# Advanced .env settings
TRACE_TIMEOUT=60                    # Extended timeout for large networks
MAX_PARALLEL_SWITCHES=10           # Parallel switch queries
DEBUG_MODE=false                   # Production vs debug logging
AUDIT_LOG_RETENTION_DAYS=90        # Audit log retention policy
```

---

## 🔐 **Security Administration**

### **Role Management:**
```python
# AD Group to Role Mapping
Role Assignment Logic:
├── Default: OSS (least privilege)
├── "SOLARWINDS_OSS_SD_ACCESS" → OSS
├── "NOC TEAM" → NetAdmin
├── Groups containing "ADMIN" → SuperAdmin
└── Manual local accounts for emergency access
```

### **Audit Trail:**
```
Audit Log Examples:
2025-01-27 10:30:15 - AUDIT - User: jdoe (netadmin) - LOGIN SUCCESS via windows_ad
2025-01-27 10:30:45 - AUDIT - User: jdoe - TRACE REQUEST - Site: MAIN, Floor: 2, MAC: 00:11:22:33:44:55
2025-01-27 10:30:47 - AUDIT - User: jdoe - MAC FOUND - 00:11:22:33:44:55 on SW-02 port Te1/0/25 [trunk]
2025-01-27 10:31:00 - AUDIT - User: jdoe - VIEW UPLINK - Te1/0/25 VLANs: 1,10,20,100-200
```

### **Security Best Practices:**
1. **Regular Access Review**: Audit user roles quarterly
2. **Switch Credential Management**: Rotate SSH credentials regularly
3. **Log Monitoring**: Review audit logs for suspicious activity
4. **Network Segmentation**: Ensure proper VLAN isolation
5. **Incident Response**: Document security events and responses

---

## 📞 **Team Responsibilities & Contacts**

### **NetAdmin Primary Responsibilities:**
- **Network Troubleshooting**: First-line advanced network support
- **Switch Management**: Configuration and maintenance of Dell switches
- **MAC Address Investigation**: Complex tracing and analysis
- **Performance Monitoring**: Switch and application performance oversight
- **Security Response**: Network security incident investigation
- **OSS Team Support**: Technical assistance and escalation handling

### **Contact Matrix:**
| Issue Type | Primary | Secondary | Method |
|------------|---------|-----------|---------|
| Application Issues | NetAdmin Team | Development Team | netadmin@company.com |
| Switch Hardware | NetAdmin Team | Vendor Support | network-ops@company.com |
| Security Incidents | NetAdmin Team | Security Team | security@company.com |
| Performance Issues | NetAdmin Team | Infrastructure Team | performance@company.com |

---

## 📚 **Advanced Documentation References**

- **[Switch Configuration Guide](switch-config-guide.md)**: Dell switch setup procedures
- **[Monitoring Playbook](monitoring-playbook.md)**: Performance monitoring procedures  
- **[Security Procedures](security-procedures.md)**: Network security protocols
- **[Troubleshooting Guide](troubleshooting-guide.md)**: Advanced problem resolution
- **[API Documentation](api-documentation.md)**: Integration and automation options

---

**Version**: 2.0.0  
**Last Updated**: January 2025  
**Team**: NetAdmin Operations Guide
