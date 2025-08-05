# Dell Port Tracer - Architecture Documentation

This directory contains architecture documentation and diagrams for the Dell Port Tracer application, organized by audience:

## Documentation Structure

### 📊 [Network Team Documentation](./network-team.md)
- **Audience**: Network administrators, network engineers
- **Focus**: Network topology, switch connections, SNMP operations, port tracing workflows
- **Key Topics**: Network discovery, switch management, port tracing logic, SNMP protocols

### 🖥️ [Server Team Documentation](./server-team.md) 
- **Audience**: System administrators, infrastructure engineers, DevOps
- **Focus**: Deployment architecture, infrastructure components, monitoring, maintenance
- **Key Topics**: Docker containers, PostgreSQL database, nginx proxy, Active Directory integration

### 👨‍💻 [Development Team Documentation](./dev-team.md)
- **Audience**: Software developers, application architects
- **Focus**: Application architecture, code structure, APIs, data flow
- **Key Topics**: Flask application, database models, authentication, frontend components

## Quick Reference

| Team | Primary Concerns | Key Components |
|------|------------------|----------------|
| **Network** | Switch connectivity, SNMP operations, port tracing accuracy | Switches, SNMP, Network topology |
| **Server** | Infrastructure, deployment, security, monitoring | Docker, PostgreSQL, nginx, AD |
| **Development** | Code architecture, APIs, data models, user experience | Flask app, database, frontend, authentication |

## System Overview

The Dell Port Tracer is a web-based application that helps network administrators trace network connections through Dell switches using SNMP protocols. The system consists of:

- **Web Application**: Flask-based Python application
- **Database**: PostgreSQL for storing switch configurations and trace history
- **Authentication**: Windows Active Directory integration
- **Infrastructure**: Docker containerized deployment with nginx reverse proxy
- **Network Integration**: SNMP-based switch discovery and port tracing

## Getting Started

1. Choose your team's documentation above
2. Review the architecture diagrams and explanations
3. Refer to the main [README.md](../README.md) for setup instructions
4. Check the [tools/](../tools/) directory for debugging and maintenance scripts

## Version Information

- **Application Version**: 2.0
- **Database**: PostgreSQL (migrated from SQLite)
- **Deployment**: Docker Compose
- **Authentication**: Windows AD/LDAP
- **Last Updated**: 2025-01-05
