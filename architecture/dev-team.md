# Dell Port Tracer - Development Team Architecture

## 👨‍💻 Development Team Overview

This documentation targets software developers and application architects, focusing on the application architecture, code structure, APIs, and data flow of the Dell Port Tracer.

## Application Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION ARCHITECTURE                     │
└─────────────────────────────────────────────────────────────────┘

          ┌──────────────────────────────────────────┐
          │        Web Client (User Browser)         │
          │                HTML/CSS/JS               │
          └─────────────────────────┬────────────────┘
                                    │
                        HTTP/HTTPS Requests
                                    │
                                    ▼
                    ┌─────────────────────────┐
                    │        nginx Proxy      │
                    └─────────────┬───────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │    Flask Application    │
                    │   Dell Port Tracer Web  │
                    └─────────────┬───────────┘
                      API Requests│
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   Business Logic Layer  │
                    └─────────────┬───────────┘
                      Database Queries│
                                      │
                                      ▼
                    ┌─────────────────────────┐
                    │     PostgreSQL DB       │
                    └─────────────────────────┘
```

## Code Structure

### Project Layout

```
DellPortTracer/
├── port_tracer_web.py          # Main Flask application
├── templates/
│   └── index.html              # Single-page application template
├── static/
│   ├── css/
│   │   └── style.css           # Main stylesheet
│   └── js/
│       └── app.js              # Frontend JavaScript
├── tools/                      # Debug and maintenance scripts
│   ├── test_ldap_connection.py # LDAP connectivity tester
│   ├── test_ad_auth.py         # AD authentication tester
│   ├── nginx_fix.py            # nginx configuration fix
│   └── debug_env.py            # Environment variable debug
├── docs/
│   ├── README.md               # Main documentation
│   └── troubleshooting.md      # Production troubleshooting guide
├── kubernetes/                 # Kubernetes deployment files
│   ├── deployment.yaml
│   ├── service.yaml
│   └── secret.yaml
├── init_db.py                  # Database initialization script
├── migrate_data.py             # SQLite to PostgreSQL migration
├── Dockerfile                  # Docker container definition
├── docker-compose.yml          # Container orchestration
├── requirements.txt            # Python dependencies
└── .env.example               # Environment variable template
```

### Key Components

- **`port_tracer_web.py`**: Main Flask application with all routes and business logic
- **`templates/index.html`**: Single-page application with embedded template logic
- **`static/`**: CSS and JavaScript assets for the frontend
- **`tools/`**: Debugging and maintenance utilities
- **`init_db.py`**: Database schema initialization
- **`migrate_data.py`**: Data migration utilities

## Data Flow

### API Endpoints

1. **Trace Port**: `/api/trace_port`
   - Method: POST
   - Input: Target MAC/IP address
   - Output: JSON with trace results

2. **Get Switches**: `/api/switches`
   - Method: GET
   - Output: JSON list of all switches

### Database Models

```python
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Switch(db.Model):
    __tablename__ = 'switches'

    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(15), nullable=False)
    snmp_community = db.Column(db.String(100), default='public')
    site = db.Column(db.String(100))
    floor = db.Column(db.String(100))

class PortTrace(db.Model):
    __tablename__ = 'port_traces'

    id = db.Column(db.Integer, primary_key=True)
    switch_id = db.Column(db.Integer, db.ForeignKey('switches.id'))
    mac_address = db.Column(db.String(17))
    port_name = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=db.func.now())
```

## API Integration

### Authentication

- **JWT Tokens**: Secure access to API endpoints
- **LDAP Authentication**: Enable login via Active Directory

### External Libraries

- **Flask**: Web framework
- **SQLAlchemy**: ORM
- **Flask-JWT-Extended**: Handle JWT
- **Flask-LDAP-Conn**: LDAP connectivity

## Development Practices

### Code Quality

- **Testing**: Pytest framework with test cases for routes and models
- **Linting**: Use of flake8 to enforce style
- **Continuous Integration**: Github Actions for automated testing

### Contribution Guidelines

- **Branching Model**: Use of feature branches
- **Pull Requests**: Mandatory code review with minimum 2 approvals
- **Commit Messages**: Follow Conventional Commits standard
