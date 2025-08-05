# Dell Port Tracer - Network Team Architecture

## 📊 Network Team Overview

This documentation focuses on the network aspects of the Dell Port Tracer application, including network topology, switch management, SNMP operations, and port tracing workflows.

## Network Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        NETWORK TOPOLOGY                         │
└─────────────────────────────────────────────────────────────────┘

    User Workstation                  Dell Port Tracer Server
    ┌──────────────┐                  ┌──────────────────────┐
    │              │   HTTPS/443      │                      │
    │  Web Browser ├──────────────────┤  nginx Reverse Proxy │
    │              │                  │                      │
    └──────────────┘                  └──────────┬───────────┘
                                                │
                                                │
                                      ┌─────────▼───────────┐
                                      │                     │
                                      │  Flask Application  │
                                      │  (Port Tracer Web)  │
                                      │                     │
                                      └─────────┬───────────┘
                                                │
                                                │ SNMP Queries
                                                │ (Port 161)
            ┌───────────────────────────────────┼───────────────────────────────────┐
            │                                   │                                   │
            ▼                                   ▼                                   ▼
    ┌──────────────┐                  ┌──────────────┐                  ┌──────────────┐
    │              │                  │              │                  │              │
    │ Dell Switch  │                  │ Dell Switch  │                  │ Dell Switch  │
    │   (Site A)   │                  │   (Site B)   │                  │   (Site C)   │
    │              │                  │              │                  │              │
    │ IP: x.x.x.x  │                  │ IP: y.y.y.y  │                  │ IP: z.z.z.z  │
    │ SNMP: v2c    │                  │ SNMP: v2c    │                  │ SNMP: v2c    │
    │              │                  │              │                  │              │
    └──────┬───────┘                  └──────┬───────┘                  └──────┬───────┘
           │                                 │                                 │
           │ Connected                       │ Connected                       │ Connected
           │ Devices                         │ Devices                         │ Devices
           ▼                                 ▼                                 ▼
    ┌─────────────┐                  ┌─────────────┐                  ┌─────────────┐
    │ End Devices │                  │ End Devices │                  │ End Devices │
    │ (PCs, APs,  │                  │ (PCs, APs,  │                  │ (PCs, APs,  │
    │  Servers)   │                  │  Servers)   │                  │  Servers)   │
    └─────────────┘                  └─────────────┘                  └─────────────┘
```

## SNMP Operations Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      SNMP QUERY WORKFLOW                        │
└─────────────────────────────────────────────────────────────────┘

1. Port Trace Request
   ┌──────────────┐      HTTP POST     ┌─────────────────┐
   │              ├───────────────────►│                 │
   │ Web Browser  │   /api/trace_port  │ Flask App       │
   │              │◄───────────────────┤                 │
   └──────────────┘      Response      └─────────┬───────┘
                                                 │
2. SNMP Discovery                                │
   ┌─────────────────────────────────────────────▼─────────────────┐
   │ For each switch in database:                                  │
   │                                                               │
   │ ┌─────────────┐    SNMP GET     ┌──────────────────────────┐  │
   │ │             ├────────────────►│                          │  │
   │ │ Port Tracer │  OID: 1.3.6.1.2.│ Dell Switch              │  │
   │ │ Application │    .1.2.2.1.6   │ (Interface Table)        │  │
   │ │             │◄────────────────┤                          │  │
   │ └─────────────┘    MAC Tables   └──────────────────────────┘  │
   │                                                               │
   │ ┌─────────────┐    SNMP GET     ┌──────────────────────────┐  │
   │ │             ├────────────────►│                          │  │
   │ │ Port Tracer │  OID: 1.3.6.1.2.│ Dell Switch              │  │
   │ │ Application │    .1.17.4.3.1  │ (Forwarding Table)       │  │
   │ │             │◄────────────────┤                          │  │
   │ └─────────────┘    Port Mapping └──────────────────────────┘  │
   │                                                               │
   └───────────────────────────────────────────────────────────────┘

3. MAC Address Resolution
   ┌───────────────────────────────────────────────────────────────┐
   │ • Query MAC address tables from all switches                 │
   │ • Match target MAC address to switch port                    │
   │ • Build connection path through network                      │
   │ • Return trace results with switch/port information          │
   └───────────────────────────────────────────────────────────────┘
```

## Switch Management Architecture

### Database Schema (Network Perspective)

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

-- Switches Table
CREATE TABLE switches (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(100) NOT NULL,
    ip_address INET NOT NULL,
    site_id INTEGER REFERENCES sites(id),
    floor_id INTEGER REFERENCES floors(id),
    snmp_community VARCHAR(100) DEFAULT 'public',
    snmp_version VARCHAR(10) DEFAULT '2c',
    enabled BOOLEAN DEFAULT true,
    model VARCHAR(100),
    location VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### SNMP Configuration

| Parameter | Value | Description |
|-----------|-------|-------------|
| **SNMP Version** | 2c | Simple Network Management Protocol version |
| **Community String** | public (default) | Authentication for SNMP access |
| **Port** | 161 | Standard SNMP port |
| **Timeout** | 5 seconds | Query timeout |
| **Retries** | 3 | Number of retry attempts |

### Key SNMP OIDs Used

| OID | Description | Usage |
|-----|-------------|-------|
| `1.3.6.1.2.1.2.2.1.6` | Interface Physical Address | Get MAC addresses of interfaces |
| `1.3.6.1.2.1.17.4.3.1` | Forwarding Database | MAC address to port mapping |
| `1.3.6.1.2.1.2.2.1.2` | Interface Description | Interface names (e.g., GigabitEthernet1/0/1) |
| `1.3.6.1.2.1.2.2.1.8` | Interface Operational Status | Port up/down status |
| `1.3.6.1.2.1.17.1.4.1.2` | Bridge Port to Interface | Bridge port mapping |

## Port Tracing Algorithm

### Tracing Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                   PORT TRACING ALGORITHM                       │
└─────────────────────────────────────────────────────────────────┘

Input: Target MAC Address or IP Address
                    │
                    ▼
          ┌─────────────────────┐
          │ 1. Validate Input   │
          │ - Check MAC format  │
          │ - Resolve IP to MAC │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │ 2. Query All        │
          │    Switches         │
          │ - Get enabled       │
          │   switches from DB  │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │ 3. SNMP Discovery   │
          │ - Connect to each   │
          │   switch via SNMP   │
          │ - Query MAC tables  │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │ 4. MAC Address      │
          │    Matching         │
          │ - Search for target │
          │   MAC in tables     │
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │ 5. Port Resolution  │
          │ - Map MAC to port   │
          │ - Get interface name│
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │ 6. Result           │
          │    Compilation      │
          │ - Switch info       │
          │ - Port details      │
          │ - Location data     │
          └─────────────────────┘
```

## Network Integration Requirements

### Switch Prerequisites

1. **SNMP Configuration**
   ```
   snmp-server community public ro
   snmp-server enable
   ```

2. **Network Connectivity**
   - Port Tracer server must have IP connectivity to all managed switches
   - SNMP port 161 must be accessible
   - No firewall blocking between server and switches

3. **Switch Support**
   - Dell PowerConnect series
   - Dell Networking N-Series
   - Standard SNMP MIB-II support

### Network Security Considerations

1. **SNMP Security**
   - Use read-only community strings
   - Consider SNMP v3 for enhanced security
   - Restrict SNMP access to Port Tracer server IP

2. **Access Control**
   - Implement network ACLs if needed
   - Monitor SNMP access logs
   - Regular community string rotation

## Troubleshooting Network Issues

### Common Network Problems

| Issue | Symptoms | Solution |
|-------|----------|----------|
| **Switch Unreachable** | Timeout errors, no response | Check IP connectivity, ping switch |
| **SNMP Access Denied** | Authentication failures | Verify community string, SNMP config |
| **Incomplete Results** | Missing switches in trace | Check switch enabled status in database |
| **Slow Performance** | Long trace times | Optimize SNMP timeouts, check network latency |

### Network Monitoring

1. **SNMP Query Performance**
   - Monitor response times
   - Track timeout rates
   - Log failed queries

2. **Switch Availability**
   - Regular connectivity checks
   - Switch status monitoring
   - Alert on unreachable switches

## Network Team Responsibilities

### Day-to-Day Operations

1. **Switch Management**
   - Add new switches to database via web interface
   - Update switch IP addresses and SNMP settings
   - Enable/disable switches as needed

2. **Monitoring**
   - Review port tracing accuracy
   - Monitor switch connectivity
   - Validate SNMP access

3. **Maintenance**
   - Update switch configurations
   - Coordinate with server team for app updates
   - Test tracing after network changes

### Integration with Network Changes

1. **New Switch Deployment**
   - Configure SNMP on new switches
   - Add switches to Port Tracer database
   - Test tracing functionality

2. **Network Topology Changes**
   - Update switch location information
   - Verify tracing paths after changes
   - Update documentation

3. **Security Updates**
   - Rotate SNMP community strings
   - Update firewall rules if needed
   - Coordinate with security team
