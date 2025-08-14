# Dell Switch Port Tracer - API Documentation

**Version:** 2.1.3  
**Last Updated:** August 2025

## Overview

The Dell Switch Port Tracer provides RESTful API endpoints for network management, MAC address tracing, VLAN management, and switch inventory control.

## Authentication

All API endpoints require session-based authentication. Users must log in through the web interface first.

### User Roles
- **OSS** (`oss`): Limited access, MAC tracing only
- **NetAdmin** (`netadmin`): Full VLAN management and inventory access
- **SuperAdmin** (`superadmin`): Full administrative access

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

### 🔧 VLAN Management (v2.1.2)

#### POST `/api/vlan/change`
Advanced VLAN change with enterprise-grade validation.

**Required Role:** NetAdmin, SuperAdmin

**Request Body:**
```json
{
  "switch_id": 1,
  "ports": "gi1/0/1-24",
  "vlan_id": 100,
  "vlan_name": "Zone_Client_Workstations",
  "description": "User Workstation Ports",
  "force_change": false,
  "skip_non_access": false
}
```

**Security Features:**
- Port format validation (prevents command injection)
- VLAN ID validation (IEEE 802.1Q standards: 1-4094)
- VLAN name validation (enterprise naming conventions)
- Description sanitization (prevents CLI injection)

**Response:**
```json
{
  "status": "success",
  "ports_changed": ["gi1/0/1", "gi1/0/2"],
  "ports_skipped": [],
  "switch_info": {
    "name": "NYC-F11-R1-VAS-01",
    "model": "Dell N3248"
  },
  "summary": "Changed 2 ports to VLAN 100"
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
