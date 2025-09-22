# Dell Port Tracer - Architecture Documentation

This directory contains architecture documentation and diagrams for the Dell Port Tracer application, organized by audience:

## Documentation Structure

### 📊 [Network Team Documentation](./network-team.md)
- **Audience**: Network administrators, network engineers
- **Focus**: Network topology, switch connections, SSH operations, port tracing workflows, VLAN management
- **Key Topics**: Network discovery, switch management, port tracing logic, SSH protocols, VLAN configuration, workflow-based operations

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
|| **Network** | Switch connectivity, SSH operations, port tracing accuracy, VLAN management | Switches, SSH, Network topology, VLAN configuration, Workflow management |
| **Server** | Infrastructure, deployment, security, monitoring | Docker, PostgreSQL, nginx, AD |
| **Development** | Code architecture, APIs, data models, user experience | Flask app, database, frontend, authentication |

## System Overview

The Dell Port Tracer is a comprehensive web-based application that helps network administrators trace network connections and manage VLANs across Dell switches using SSH-based secure communication. The system consists of:

- **Web Application**: Flask-based Python application with advanced VLAN management capabilities and enhanced session timeout handling
- **Database**: PostgreSQL for storing switch configurations, trace history, and VLAN management audit logs
- **Authentication**: Windows Active Directory integration with role-based access control
- **Session Management**: Proactive session timeout warnings, cross-tab state management, and graceful session expiration handling
- **Infrastructure**: Docker containerized deployment with nginx reverse proxy
- **Network Integration**: SSH-based switch communication with comprehensive Dell switch model support
- **VLAN Manager**: Enterprise-grade VLAN configuration and port management system with workflow-based operations (onboarding/offboarding)
- **Security Framework**: Multi-layer input validation and command injection prevention
- **Professional UI**: Select2-powered dropdowns with intelligent styling, perfect text alignment, and cross-browser consistency
- **User Experience**: Real-time dynamic updates, contextual help text, and optimized search functionality
- **State Management**: Frontend UI state preservation system for sidebar navigation context during operations
- **Version Management**: Centralized version control system with single source of truth in `app/__init__.py` and programmatic access via `get_version.py` utility

## Getting Started

1. Choose your team's documentation above
2. Review the architecture diagrams and explanations
3. Refer to the main [README.md](../README.md) for setup instructions
4. Check the [tools/](../tools/) directory for debugging and maintenance scripts

## Version Information

- **Application Version**: 2.2.2
- **Architecture**: 3-Container Production Setup (app, nginx, postgres)
- **Database**: PostgreSQL with persistent named volumes
- **Deployment**: Docker Compose with SSL/HTTPS support
- **Authentication**: Windows AD/LDAP + Local accounts
- **Security**: SSL/HTTPS enabled, automated certificate generation
- **Backup**: Automated backup and rollback with deploy-safe.sh
- **Session Timeout**: 5-minute configurable timeout with user-friendly warning system
- **Frontend Enhancements**: JavaScript-based session state management and keep-alive functionality
- **UI State Preservation**: Site tree navigation state maintained during switch management operations
- **Workflow Management**: Structured onboarding and offboarding workflows with port enable/disable automation
- **Last Updated**: September 22, 2025
