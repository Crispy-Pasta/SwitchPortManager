# Dell Port Tracer - Network Team Architecture

## 📊 Network Team Overview

This documentation focuses on the network aspects of the Dell Port Tracer application, including network topology, switch management, SSH-based operations, port tracing workflows, and advanced VLAN management capabilities for the v2.1.3 Docker-deployed architecture.

## Network Architecture Diagram (v2.1.3)

```
┌─────────────────────────────────────────────────────────────────┐
│                  NETWORK TOPOLOGY - v2.1.3                     │
│                  3-Container Production Stack                   │
└─────────────────────────────────────────────────────────────────┘

    User Workstations              Dell Port Tracer Docker Host
    ┌──────────────┐              ┌────────────────────────────────┐
    │              │   HTTPS/443  │ ┌──────────────────────────┐   │
    │  Web Browser ├──────────────┼─┤ dell-port-tracer-nginx  │   │
    │              │   HTTP/80    │ │ • SSL Termination       │   │
    └──────────────┘   (redirect) │ │ • Reverse Proxy         │   │
                                  │ │ • Security Headers      │   │
    ┌──────────────┐              │ └────────┬─────────────────┘   │
    │              │              │          │ Proxy Pass          │
    │  Admin Users │              │          │ (app:5000)          │
    │   (Network   │              │          ▼                     │
    │    Team)     │              │ ┌──────────────────────────┐   │
    └──────────────┘              │ │ dell-port-tracer-app     │   │
                                  │ │ • Flask Web Application  │   │
    ┌──────────────┐              │ │ • SSH to Dell Switches   │   │
    │              │              │ │ • AD/LDAP Authentication │   │
    │ Regular Users│              │ │ • Port Tracing Logic     │   │
    │   (IT Staff) │              │ └────────┬─────────────────┘   │
    └──────────────┘              │          │ PostgreSQL          │
                                  │          │ Connection          │
                                  │          ▼                     │
                                  │ ┌──────────────────────────┐   │
                                  │ │ dell-port-tracer-postgres│   │
                                  │ │ • PostgreSQL 15 Database │   │
                                  │ │ • Switch Inventory       │   │
                                  │ │ • Audit Logs            │   │
                                  │ │ • Persistent Storage     │   │
                                  │ └──────────────────────────┘   │
                                  └────────────────────────────────┘
                                           │
                                           │ SSH Connections
                                           │ (Port 22)
            ┌──────────────────────────────┼──────────────────────────────┐
            │                              │                              │
            ▼                              ▼                              ▼
    ┌──────────────┐            ┌──────────────┐            ┌──────────────┐
    │              │            │              │            │              │
    │ Dell Switch  │            │ Dell Switch  │            │ Dell Switch  │
    │   (Site A)   │            │   (Site B)   │            │   (Site C)   │
    │              │            │              │            │              │
    │ IP: x.x.x.x  │            │ IP: y.y.y.y  │            │ IP: z.z.z.z  │
    │ SSH: Port 22 │            │ SSH: Port 22 │            │ SSH: Port 22 │
    │ OS10/EOS     │            │ OS10/EOS     │            │ OS10/EOS     │
    │              │            │              │            │              │
    └──────┬───────┘            └──────┬───────┘            └──────┬───────┘
           │                           │                           │
           │ Connected                 │ Connected                 │ Connected
           │ Devices                   │ Devices                   │ Devices
           ▼                           ▼                           ▼
    ┌─────────────┐            ┌─────────────┐            ┌─────────────┐
    │ End Devices │            │ End Devices │            │ End Devices │
    │ (PCs, APs,  │            │ (PCs, APs,  │            │ (PCs, APs,  │
    │  Servers)   │            │  Servers)   │            │  Servers)   │
    └─────────────┘            └─────────────┘            └─────────────┘

          Corporate Network Infrastructure
    ┌─────────────────────────────────────────────┐
    │  Windows Active Directory Domain           │
    │  • LDAP Authentication (389/636)           │
    │  • User Account Management                  │
    │  • Group Policy Integration                 │
    └─────────────────────────────────────────────┘
```

## SSH Operations Flow (v2.1.3)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SSH-BASED QUERY WORKFLOW                     │
└─────────────────────────────────────────────────────────────────┘

1. Port Trace Request
   ┌──────────────┐      HTTP POST     ┌─────────────────┐
   │              ├───────────────────►│                 │
   │ Web Browser  │   /api/trace_port  │ Flask App       │
   │              │◄───────────────────┤ (Docker)        │
   └──────────────┘      Response      └─────────┬───────┘
                                                 │
2. SSH Discovery & Command Execution             │
   ┌─────────────────────────────────────────────▼─────────────────┐
   │ For each switch in database:                                  │
   │                                                               │
   │ ┌─────────────┐    SSH (Port 22) ┌──────────────────────────┐  │
   │ │             ├────────────────►│                          │  │
   │ │ Port Tracer │ show mac         │ Dell Switch (OS10/EOS)  │  │
   │ │ Application │ address-table    │ SSH Server               │  │
   │ │             │◄────────────────┤                          │  │
   │ └─────────────┘ MAC Table Output └──────────────────────────┘  │
   │                                                               │
   │ ┌─────────────┐    SSH (Port 22) ┌──────────────────────────┐  │
   │ │             ├────────────────►│                          │  │
   │ │ Port Tracer │ show interface   │ Dell Switch (OS10/EOS)  │  │
   │ │ Application │ status           │ SSH Server               │  │
   │ │             │◄────────────────┤                          │  │
   │ └─────────────┘ Port Status      └──────────────────────────┘  │
   │                                                               │
   │ ┌─────────────┐    SSH (Port 22) ┌──────────────────────────┐  │
   │ │             ├────────────────►│                          │  │
   │ │ Port Tracer │ show interface   │ Dell Switch (OS10/EOS)  │  │
   │ │ Application │ description      │ SSH Server               │  │
   │ │             │◄────────────────┤                          │  │
   │ └─────────────┘ Port Details     └──────────────────────────┘  │
   │                                                               │
   └───────────────────────────────────────────────────────────────┘

3. MAC Address Resolution & Port Identification
   ┌───────────────────────────────────────────────────────────────┐
   │ • Execute 'show mac address-table' on all switches           │
   │ • Parse command output for target MAC address                │
   │ • Extract port information and VLAN details                  │
   │ • Get additional port descriptions and status                │
   │ • Build comprehensive trace results with location data       │
   │ • Store audit log in PostgreSQL database                     │
   └───────────────────────────────────────────────────────────────┘
```

## Switch Management Architecture

### Database Schema (Network Perspective - v2.1.3)

```sql
-- Sites Table
CREATE TABLE sites (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Floors Table
CREATE TABLE floors (
    id SERIAL PRIMARY KEY,
    site_id INTEGER REFERENCES sites(id),
    name VARCHAR(100) NOT NULL,
    description TEXT
);

-- Switches Table (Updated for SSH-based access)
CREATE TABLE switches (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(100) NOT NULL,
    ip_address INET NOT NULL UNIQUE,
    ssh_username VARCHAR(100) NOT NULL,
    ssh_password VARCHAR(255) NOT NULL, -- Encrypted with Fernet
    device_type VARCHAR(50) DEFAULT 'dell_os10',
    site_id INTEGER REFERENCES sites(id),
    floor_id INTEGER REFERENCES floors(id),
    building VARCHAR(100),
    status VARCHAR(20) DEFAULT 'active',
    model VARCHAR(100),
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Port Traces Table (Enhanced for audit logging)
CREATE TABLE port_traces (
    id SERIAL PRIMARY KEY,
    switch_id INTEGER REFERENCES switches(id),
    mac_address VARCHAR(17) NOT NULL,
    ip_address VARCHAR(15),
    port_name VARCHAR(50),
    vlan_id INTEGER,
    trace_result TEXT, -- JSON string of complete results
    user_id VARCHAR(100), -- AD username
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audit Logs Table
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(50),
    details TEXT,
    ip_address INET,
    user_agent VARCHAR(500),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### SSH Configuration (v2.1.3)

| Parameter | Value | Description |
|-----------|-------|-------------|
| **SSH Port** | 22 | Standard SSH port |
| **Device Type** | dell_os10 | Netmiko device type for Dell OS10/EOS |
| **Timeout** | 30 seconds | SSH connection timeout |
| **Auth Timeout** | 30 seconds | SSH authentication timeout |
| **Connection Timeout** | 10 seconds | Initial connection timeout |
| **Keepalive** | 30 seconds | SSH keepalive interval |
| **Fast CLI** | False | Disable fast CLI mode for stability |

### Key Dell OS10 Commands Used

| Command | Description | Usage |
|---------|-------------|-------|
| `show mac address-table` | Display MAC address forwarding table | Primary command for MAC address location |
| `show interface status` | Show interface operational status | Get port up/down status |
| `show interface description` | Show interface descriptions | Get port descriptions and labels |
| `show interface ethernet X/X/X` | Show detailed interface information | Get specific port details |
| `show vlan` | Display VLAN configuration | Get VLAN membership information |
| `show running-config interface X/X/X` | Show interface configuration | Get port mode and VLAN assignments |
| `interface range X/X/X-X` | Configure multiple interfaces | Batch VLAN configuration |
| `switchport access vlan X` | Set access VLAN | VLAN assignment command |
| `vlan X` | Create/configure VLAN | VLAN management command |

## Port Tracing Algorithm

### Tracing Workflow (v2.1.3 SSH-Based)

```
┌─────────────────────────────────────────────────────────────────┐
│                 SSH-BASED PORT TRACING ALGORITHM               │
└─────────────────────────────────────────────────────────────────┘

Input: Target MAC Address or IP Address
                    │
                    ▼
          ┌─────────────────────────┐
          │ 1. Input Validation       │
          │ - Normalize MAC format    │
          │ - Validate MAC address    │
          │ - Check IP to MAC (ARP)   │
          └────────────┬────────────┘
                     │
                     ▼
          ┌─────────────────────────┐
          │ 2. Switch Discovery       │
          │ - Query PostgreSQL DB     │
          │ - Get active switches     │
          │ - Load SSH credentials    │
          └────────────┬────────────┘
                     │
                     ▼
          ┌─────────────────────────┐
          │ 3. SSH Connection         │
          │ - Connect via Netmiko     │
          │ - Authenticate with       │
          │   encrypted credentials   │
          └────────────┬────────────┘
                     │
                     ▼
          ┌─────────────────────────┐
          │ 4. Command Execution      │
          │ - show mac address-table  │
          │ - Parse CLI output        │
          │ - Extract MAC/port data   │
          └────────────┬────────────┘
                     │
                     ▼
          ┌─────────────────────────┐
          │ 5. Data Enrichment        │
          │ - Get port descriptions   │
          │ - Check port status       │
          │ - Get VLAN information    │
          └────────────┬────────────┘
                     │
                     ▼
          ┌─────────────────────────┐
          │ 6. Result Assembly        │
          │ - Combine all data        │
          │ - Add location info       │
          │ - Store audit log        │
          │ - Return JSON response    │
          └─────────────────────────┘
```

## Network Integration Requirements (v2.1.3)

### Switch Prerequisites

1. **SSH Configuration**
   ```bash
   # Dell OS10 SSH Configuration
   ip ssh server enable
   username admin password encrypted-password role sysadmin
   username admin privilege 15
   ```

2. **Network Connectivity**
   - Port Tracer Docker host must have IP connectivity to all managed switches
   - SSH port 22 must be accessible from Docker containers
   - No firewall blocking between Docker host and switches
   - Network routing configured for multi-site switch access

3. **Switch Support (v2.1.3)**
   - Dell PowerConnect series (Legacy support)
   - Dell Networking N-Series with OS10
   - Dell Enterprise SONiC switches
   - Any switch supporting standard Dell OS10 CLI commands

### Network Security Considerations (v2.1.3)

1. **SSH Security**
   - Use dedicated service accounts for Port Tracer access
   - Implement SSH key-based authentication where possible
   - Restrict SSH access to Port Tracer server IP addresses
   - Regular password rotation for SSH accounts
   - Monitor SSH access logs for suspicious activity

2. **Container Network Security**
   - Docker container network isolation
   - Firewall rules for container-to-switch communication
   - VPN connectivity for remote site switches
   - Network segmentation for management traffic

3. **Credential Management**
   - Switch credentials encrypted at rest using Fernet
   - Secure credential storage in PostgreSQL database
   - Environment variable protection for sensitive data
   - Regular audit of stored credentials

## Troubleshooting Network Issues (v2.1.3)

### Common Network Problems

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Switch Unreachable** | SSH timeout errors, connection refused | Check IP connectivity, ping switch, verify SSH service |
| **SSH Authentication Failed** | Login failures, permission denied | Verify username/password, check account privileges |
| **Incomplete Results** | Missing switches in trace | Check switch status in database, verify SSH connectivity |
| **Slow Performance** | Long trace times, timeouts | Optimize SSH timeouts, check network latency, review switch load |
| **Container Network Issues** | Docker connectivity problems | Check Docker network configuration, verify container networking |
| **SSL Certificate Problems** | HTTPS access issues | Verify SSL certificates, check nginx configuration |

### Network Monitoring

1. **SSH Connection Performance**
   - Monitor SSH connection establishment times
   - Track SSH authentication success rates
   - Log failed SSH connection attempts
   - Alert on repeated connection failures

2. **Switch Availability**
   - Regular ping checks from Docker host
   - SSH connectivity verification
   - Switch response time monitoring
   - Alert on unreachable switches

3. **Docker Container Health**
   - Monitor container networking status
   - Track container resource usage
   - Check inter-container communication
   - Database connectivity monitoring

## VLAN Management Capabilities (v2.1.3)

### Advanced VLAN Management Features

The Dell Port Tracer v2.1.3 includes comprehensive VLAN management capabilities designed for network administrators to safely configure and manage VLAN assignments across Dell switches.

### VLAN Management Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  VLAN MANAGEMENT WORKFLOW                       │
└─────────────────────────────────────────────────────────────────┘

1. VLAN Assignment Request
   ┌──────────────┐      HTTP POST     ┌─────────────────┐
   │              ├───────────────────►│                 │
   │ Web Browser  │   /api/vlan_config │ Flask App       │
   │              │◄───────────────────┤ (Docker)        │
   └──────────────┘   Preview Response  └─────────┬───────┘
                                                 │
2. Switch Configuration via SSH                   │
   ┌─────────────────────────────────────────────▼─────────────────┐
   │ Safety checks & validation:                                   │
   │                                                               │
   │ ┌─────────────┐    SSH Commands   ┌──────────────────────────┐  │
   │ │             ├────────────────►│                          │  │
   │ │ VLAN Config │ show vlan         │ Dell Switch (OS10/EOS)  │  │
   │ │ Module      │ show running-     │ SSH Server               │  │
   │ │             │ config interface  │                          │  │
   │ │             │◄────────────────┤                          │  │
   │ └─────────────┘ Validation Data   └──────────────────────────┘  │
   │                                                               │
   │ ┌─────────────┐    SSH Config     ┌──────────────────────────┐  │
   │ │             ├────────────────►│                          │  │
   │ │ VLAN Config │ interface range   │ Dell Switch (OS10/EOS)  │  │
   │ │ Module      │ switchport access │ SSH Server               │  │
   │ │             │ vlan X            │                          │  │
   │ │             │◄────────────────┤                          │  │
   │ └─────────────┘ Config Results    └──────────────────────────┘  │
   │                                                               │
   └───────────────────────────────────────────────────────────────┘

3. Configuration Validation & Audit
   ┌───────────────────────────────────────────────────────────────┐
   │ • Verify VLAN exists before assignment                       │
   │ • Check port status and current configuration                │
   │ • Validate uplink port protection (prevent misconfigurations)│
   │ • Execute configuration commands with error handling          │
   │ • Store complete audit trail in PostgreSQL database          │
   │ • Return success/failure status with detailed feedback       │
   └───────────────────────────────────────────────────────────────┘
```

### VLAN Configuration Features

#### 1. **Safe VLAN Assignment**
- **Pre-validation**: Checks if target VLAN exists on switch before assignment
- **Port status verification**: Ensures ports are accessible and configurable
- **Uplink protection**: Prevents accidental configuration of uplink/trunk ports
- **Rollback capability**: Ability to undo configurations if needed

#### 2. **Switch Model Awareness**
- **Dell OS10 Support**: Full compatibility with Dell OS10/EOS command syntax
- **Legacy PowerConnect**: Support for older Dell PowerConnect switches
- **Dynamic command adaptation**: Adjusts commands based on switch model/version
- **Error handling**: Switch-specific error detection and reporting

#### 3. **Real-time Port Management**
- **Live port status**: Real-time checking of port operational status
- **Interface descriptions**: Automatic retrieval of port descriptions/labels
- **VLAN membership**: Current VLAN assignment verification
- **Configuration preview**: Shows proposed changes before execution

#### 4. **Security Framework**
- **Input validation**: Comprehensive validation of all user inputs
- **Command injection prevention**: Parameterized commands to prevent injection attacks
- **Authentication integration**: LDAP/AD authentication for access control
- **Audit logging**: Complete audit trail of all configuration changes

### VLAN Management Commands

#### Dell OS10 VLAN Commands Used

| Command | Purpose | Safety Level |
|---------|---------|-------------|
| `show vlan` | Verify VLAN existence | **Safe** - Read-only |
| `show running-config interface X/X/X` | Check current configuration | **Safe** - Read-only |
| `show interface status` | Verify port status | **Safe** - Read-only |
| `interface range X/X/X-X` | Select multiple interfaces | **Config** - Configuration mode |
| `switchport access vlan X` | Assign access VLAN | **Config** - Modifies switch |
| `end` | Exit configuration mode | **Safe** - Exit config |
| `write memory` | Save configuration | **Config** - Saves changes |

#### VLAN Assignment Workflow

```bash
# 1. Validation Phase (Read-only commands)
show vlan brief                               # Verify VLAN exists
show interface status                         # Check port status
show running-config interface ethernet 1/1/1 # Get current config

# 2. Configuration Phase (Modify commands)
configure terminal                            # Enter config mode
interface range ethernet 1/1/1-1/1/5        # Select port range
switchport access vlan 100                   # Assign VLAN
end                                          # Exit config mode
write memory                                 # Save configuration
```

### VLAN Management Safety Features

#### 1. **Uplink Port Protection**
- **Automatic detection**: Identifies potential uplink/trunk ports
- **Configuration blocking**: Prevents VLAN changes on critical uplinks
- **Manual override**: Admin override capability with additional confirmation
- **Port role validation**: Checks if port is configured as trunk/access

#### 2. **Input Validation**
- **VLAN ID range**: Validates VLAN IDs (1-4094) are within acceptable range
- **Port format**: Ensures proper Ethernet port format (e.g., 1/1/1)
- **Switch connectivity**: Verifies switch is reachable before configuration
- **User permissions**: Validates user has required privileges for VLAN management

#### 3. **Error Handling & Recovery**
- **Command validation**: Pre-validates all commands before execution
- **Partial failure handling**: Handles scenarios where some ports succeed/fail
- **Configuration rollback**: Ability to restore previous configuration
- **Detailed error reporting**: Provides specific error messages for troubleshooting

### VLAN Management Database Integration

#### Enhanced Audit Trail

```sql
-- VLAN Configuration Audit Table
CREATE TABLE vlan_configuration_logs (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    switch_id INTEGER REFERENCES switches(id),
    action VARCHAR(50) NOT NULL, -- 'assign', 'remove', 'preview'
    ports TEXT NOT NULL,         -- JSON array of ports
    vlan_id INTEGER NOT NULL,
    previous_config TEXT,        -- Previous VLAN assignments
    new_config TEXT,             -- New VLAN assignments
    success BOOLEAN NOT NULL,
    error_message TEXT,
    commands_executed TEXT,      -- Actual commands sent to switch
    execution_time FLOAT,        -- Time taken for configuration
    ip_address INET,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- VLAN Inventory Table (Optional)
CREATE TABLE vlan_inventory (
    id SERIAL PRIMARY KEY,
    switch_id INTEGER REFERENCES switches(id),
    vlan_id INTEGER NOT NULL,
    vlan_name VARCHAR(100),
    description TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(switch_id, vlan_id)
);
```

### Network Team VLAN Management Procedures

#### 1. **Daily VLAN Operations**
- **Port assignment requests**: Process user requests for VLAN changes
- **Configuration validation**: Verify VLAN assignments are correct
- **Audit log review**: Monitor VLAN configuration changes
- **Error investigation**: Troubleshoot failed VLAN assignments

#### 2. **VLAN Planning & Management**
- **VLAN inventory maintenance**: Keep VLAN database current
- **New VLAN creation**: Add VLANs to switches before assignment
- **VLAN cleanup**: Remove unused VLANs to maintain clean configuration
- **Documentation updates**: Maintain VLAN assignment documentation

#### 3. **Security & Compliance**
- **Access control**: Ensure only authorized users can modify VLANs
- **Change approval**: Implement change management for VLAN modifications
- **Configuration backup**: Regular backup of switch configurations
- **Compliance reporting**: Generate reports for security audits

#### 4. **Troubleshooting VLAN Issues**

| Issue | Symptoms | Resolution |
|-------|----------|------------|
| **VLAN Not Found** | "VLAN does not exist" error | Create VLAN on switch first, then retry assignment |
| **Port Access Denied** | SSH permission errors | Verify switch credentials and user privileges |
| **Uplink Protection Block** | "Uplink port detected" warning | Use admin override or verify port is not uplink |
| **Partial Configuration** | Some ports succeed, others fail | Check individual port status and rerun failed ports |
| **Configuration Not Saved** | Changes lost after reboot | Ensure "write memory" command executed successfully |

## Network Team Responsibilities (v2.1.3)

### Day-to-Day Operations

1. **Switch Management**
   - Add new switches to database via secure web interface
   - Update switch IP addresses and SSH credentials
   - Enable/disable switches based on maintenance schedules
   - Verify switch inventory accuracy

2. **Security & Monitoring**
   - Review port tracing accuracy and audit logs
   - Monitor SSH connection success rates
   - Validate user access and authentication
   - Track application usage statistics

3. **Maintenance & Updates**
   - Coordinate switch firmware updates
   - Update SSH credentials as per security policy
   - Test tracing functionality after network changes
   - Coordinate with DevOps team for application updates

### Integration with Network Changes

1. **New Switch Deployment**
   - Configure SSH access on new Dell switches
   - Create service accounts with appropriate privileges
   - Add switches to Port Tracer database with encrypted credentials
   - Test complete port tracing workflow

2. **Network Infrastructure Updates**
   - Update switch location and site information
   - Verify connectivity after topology changes
   - Update firewall rules for new network segments
   - Test Docker container network access

3. **Security & Compliance Updates**
   - Regular SSH credential rotation per security policy
   - Update firewall ACLs for container access
   - Coordinate SSL certificate renewals
   - Review and update network access logging

### Docker Environment Management

1. **Container Networking**
   - Verify Docker container network connectivity
   - Monitor inter-container communication (app ↔ postgres, nginx ↔ app)
   - Ensure proper DNS resolution within containers
   - Test external network access from containers

2. **Production Deployment Coordination**
   - Coordinate with DevOps team for application updates
   - Test network connectivity after container updates
   - Verify switch access after Docker host changes
   - Validate SSL/HTTPS functionality after nginx updates
