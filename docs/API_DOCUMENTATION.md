# Dell Switch Port Tracer - API Documentation

**Version:** 2.2.1  
**Last Updated:** September 2025
**Architecture:** Docker Compose 3-Container Stack  
**Database:** PostgreSQL with encrypted credentials

## Overview

The Dell Switch Port Tracer v2.1.3 provides RESTful API endpoints for SSH-based network management, MAC address tracing, switch inventory control, and comprehensive audit logging. The application uses secure SSH connections to Dell switches and PostgreSQL for persistent storage.

## Architecture

### Production Stack
- **dell-port-tracer-nginx**: SSL/HTTPS termination and reverse proxy
- **dell-port-tracer-app**: Flask application with SSH connectivity
- **dell-port-tracer-postgres**: PostgreSQL database with persistent storage

### Key Features
- ✅ SSH-based switch communication (replaced SNMP)
- ✅ Windows AD/LDAP authentication
- ✅ PostgreSQL database with encrypted credentials
- ✅ SSL/HTTPS with automatic certificates
- ✅ Comprehensive audit logging
- ✅ Role-based access control

## Authentication

All API endpoints require session-based authentication. Users must log in through the web interface first.

### User Roles
- **OSS** (`oss`): Limited access, view access ports only
- **NetAdmin** (`netadmin`): Full network access including uplinks and VLANs
- **SuperAdmin** (`superadmin`): Complete administrative access and system management

## API Endpoints

### 🔍 MAC Address Tracing

#### POST `/trace`
Trace MAC address across switches in a specified site and floor.

**Required Role:** OSS, NetAdmin, SuperAdmin

**Request Body:**
```json
{
  "site": "SITE_NAME",
  "floor": "FLOOR_NAME", 
  "mac": "aa:bb:cc:dd:ee:ff"
}
```

**Response:**
```json
[
  {
    "switch_name": "SWITCH-F11-R1-VAS-01",
    "switch_ip": "10.50.11.10",
    "status": "found",
    "port": "Gi1/0/24",
    "vlan": "100",
    "port_description": "User Workstation",
    "port_mode": "access",
    "is_uplink": false
  }
]
```

**Status Codes:**
- `200` - Success
- `400` - Invalid MAC format or missing fields
- `401` - Not authenticated
- `503` - High CPU load, request rejected

---

### 🏢 Switch Inventory Management

#### GET `/api/sites`
Retrieve all sites and their floors.

**Required Role:** NetAdmin, SuperAdmin

**Response:**
```json
[
  {
    "id": 1,
    "name": "NYC_MAIN",
    "floors": [
      {
        "id": 1,
        "name": "11"
      }
    ]
  }
]
```

#### POST `/api/sites`
Create a new site.

**Required Role:** NetAdmin, SuperAdmin

**Request Body:**
```json
{
  "name": "NYC_MAIN"
}
```

#### PUT `/api/sites/{site_id}`
Update an existing site.

#### DELETE `/api/sites/{site_id}`
Delete a site and all associated floors and switches.

---

#### POST `/api/floors`
Create a new floor in a site.

**Required Role:** NetAdmin, SuperAdmin

**Request Body:**
```json
{
  "name": "11",
  "site_id": 1
}
```

#### PUT `/api/floors/{floor_id}`
Update an existing floor.

#### DELETE `/api/floors/{floor_id}`
Delete a floor and all associated switches.

---

#### GET `/api/switches`
Retrieve all switches with site and floor information.

**Required Role:** NetAdmin, SuperAdmin

**Response:**
```json
[
  {
    "id": 1,
    "name": "NYC-F11-R1-VAS-01",
    "ip_address": "10.50.11.10",
    "model": "Dell N3248",
    "description": "Floor 11 VAS Switch",
    "enabled": true,
    "site_name": "NYC_MAIN",
    "floor_name": "11",
    "site_id": 1,
    "floor_id": 1
  }
]
```

#### POST `/api/switches`
Create a new switch.

**Request Body:**
```json
{
  "name": "NYC-F11-R1-VAS-01",
  "ip_address": "10.50.11.10", 
  "model": "Dell N3248",
  "description": "Floor 11 VAS Switch",
  "enabled": true,
  "floor_id": 1
}
```

#### PUT `/api/switches/{switch_id}`
Update an existing switch.

#### DELETE `/api/switches/{switch_id}`
Delete a switch from inventory.

---

### 🔧 VLAN Management (v2.1.3)

#### POST `/api/vlan_config`
Enterprise VLAN configuration with preview-execute workflow and enhanced safety features.

**Required Role:** NetAdmin, SuperAdmin

**Request Body:**
```json
{
  "switch_id": 1,
  "ports": "ethernet 1/1/1-1/1/24",
  "vlan_id": 100,
  "action": "preview|execute",
  "include_vlan_name": true,
  "override_uplink_protection": false,
  "skip_non_access_ports": true
}
```

**Enhanced Security Features (v2.1.3):**
- Advanced port format validation with Dell OS10/EOS syntax
- VLAN existence verification before assignment
- Uplink port protection with override capability
- Real-time port status validation
- Command injection prevention with parameterized queries
- Comprehensive audit logging with execution time tracking

**Preview Response:**
```json
{
  "action": "preview",
  "status": "ready_for_execution",
  "switch_info": {
    "name": "NYC-F11-R1-VAS-01",
    "ip_address": "10.50.11.10",
    "model": "Dell N3248TE-ON"
  },
  "vlan_info": {
    "vlan_id": 100,
    "vlan_name": "Production_Workstations",
    "exists": true
  },
  "port_analysis": {
    "total_ports_requested": 24,
    "valid_ports": 22,
    "uplink_ports_detected": 2,
    "ports_to_configure": [
      {
        "port": "ethernet 1/1/1",
        "current_vlan": "1",
        "target_vlan": "100",
        "status": "up",
        "description": "User Workstation",
        "mode": "access",
        "action": "change_vlan"
      }
    ],
    "ports_to_skip": [
      {
        "port": "ethernet 1/1/23",
        "reason": "uplink_port",
        "current_config": "trunk",
        "override_available": true
      }
    ]
  },
  "configuration_preview": {
    "commands_to_execute": [
      "configure terminal",
      "interface range ethernet 1/1/1-1/1/22",
      "switchport access vlan 100",
      "end",
      "write memory"
    ],
    "estimated_execution_time": "15-30 seconds",
    "rollback_available": true
  },
  "safety_checks": {
    "vlan_exists": true,
    "switch_reachable": true,
    "uplink_protection_active": true,
    "all_validations_passed": true
  }
}
```

**Execute Response:**
```json
{
  "action": "execute",
  "status": "success",
  "execution_summary": {
    "ports_configured": 22,
    "ports_skipped": 2,
    "execution_time": 18.5,
    "commands_executed": 5,
    "configuration_saved": true
  },
  "switch_info": {
    "name": "NYC-F11-R1-VAS-01",
    "ip_address": "10.50.11.10",
    "model": "Dell N3248TE-ON"
  },
  "vlan_info": {
    "vlan_id": 100,
    "vlan_name": "Production_Workstations"
  },
  "configured_ports": [
    {
      "port": "ethernet 1/1/1",
      "previous_vlan": "1",
      "new_vlan": "100",
      "status": "success"
    }
  ],
  "skipped_ports": [
    {
      "port": "ethernet 1/1/23",
      "reason": "uplink_protection",
      "status": "skipped"
    }
  ],
  "audit_log_id": "vlan-config-20250814-095832",
  "rollback_info": {
    "available": true,
    "rollback_id": "rb-20250814-095832",
    "expires_at": "2025-08-15T09:58:32Z"
  }
}
```

#### POST `/api/vlan/check`
Check if a VLAN exists on a switch.

**Required Role:** NetAdmin, SuperAdmin

**Request Body:**
```json
{
  "switch_id": 1,
  "vlan_id": 100
}
```

**Response:**
```json
{
  "exists": true,
  "vlan_id": 100,
  "vlan_name": "Zone_Client_Workstations",
  "status": "active"
}
```

#### POST `/api/port/status`
Get detailed port status information.

**Required Role:** NetAdmin, SuperAdmin

**Request Body:**
```json
{
  "switch_id": 1,
  "ports": "gi1/0/1-5"
}
```

**Response:**
```json
{
  "ports": [
    {
      "port": "gi1/0/1",
      "status": "up",
      "mode": "access",
      "vlan": "100",
      "description": "User Workstation",
      "is_uplink": false
    }
  ],
  "switch_model": "Dell N3248",
  "switch_name": "NYC-F11-R1-VAS-01"
}
```

---

### 📊 System Monitoring

#### GET `/cpu-status`
CPU monitoring status for administrators.

**Required Role:** NetAdmin, SuperAdmin

**Response:**
```json
{
  "current_load": 35.2,
  "status": "green",
  "can_accept_requests": true,
  "thresholds": {
    "green": 40,
    "yellow": 60, 
    "red": 80
  }
}
```

#### GET `/switch-protection-status`
Switch protection monitoring status.

**Required Role:** NetAdmin, SuperAdmin

#### GET `/health`
Application health check endpoint.

**Public Access:** No authentication required

**Response:**
```json
{
  "status": "healthy",
  "version": "2.1.3",
  "timestamp": "2025-08-14T09:58:10Z"
}
```

---

## Input Validation & Security

### MAC Address Format
- **Valid:** `aa:bb:cc:dd:ee:ff`, `AA-BB-CC-DD-EE-FF`, `aabb.ccdd.eeff`
- **Invalid:** Partial addresses, special characters, SQL injection attempts

### Port Format Validation
- **Valid:** `gi1/0/1`, `gi1/0/1-24`, `te1/0/1`, `tw1/0/1`
- **Invalid:** Non-standard formats, command injection attempts

### VLAN ID Validation  
- **Range:** 1-4094 (IEEE 802.1Q standard)
- **Excluded:** 0 (reserved), 4095 (reserved)

### VLAN Name Validation
- **Pattern:** Enterprise naming conventions
- **Examples:** `Zone_Client_Name`, `VLAN_100_Workstations`
- **Invalid:** Special characters that could cause CLI injection

## Error Handling

### Standard Error Response
```json
{
  "error": "Detailed error message",
  "error_type": "validation_error|authentication_error|system_error"
}
```

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized 
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `500` - Internal Server Error
- `503` - Service Unavailable (high CPU load)

## Rate Limiting & Concurrency

### Site-based Limits
- **Max concurrent users per site:** 10 (configurable)
- **Max workers per site:** 8 (Dell switch SSH limit)
- **CPU protection:** Automatic request rejection when load > 80%

### Switch Protection
- **Max connections per switch:** 8 (configurable)
- **Commands per second limit:** 10 (configurable)
- **Total connection limit:** 64 (global)

## Audit Logging

All API operations are logged to `audit.log` with:
- User identification and role
- Action performed and parameters
- Success/failure status
- Timestamp and duration
- Security violations and injection attempts

**Optional:** Syslog integration for SolarWinds SEM compatibility.
