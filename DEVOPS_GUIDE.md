# Dell Port Tracer - DevOps Deployment Guide

## Environment Variables Required

The application requires the following environment variables to be configured in the production environment:

### Required Variables

| Variable | Description | Example Value |
|----------|-------------|---------------|
| `SECRET_KEY` | Flask secret key for session management | Generated with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `POSTGRES_DB` | PostgreSQL database name | `dell_port_tracer` |
| `POSTGRES_USER` | PostgreSQL username | `dell_user` |
| `POSTGRES_PASSWORD` | PostgreSQL password | *Secure password* |
| `POSTGRES_HOST` | PostgreSQL host | `localhost` or database server IP |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `DATABASE_URL` | Full database connection string | `postgresql://user:pass@host:port/dbname` |
| `SWITCH_USERNAME` | Network switch login username | *Network device credentials* |
| `SWITCH_PASSWORD` | Network switch login password | *Network device credentials* |

### Optional Variables

| Variable | Description | Default Value |
|----------|-------------|---------------|
| `FLASK_ENV` | Flask environment | `production` |
| `FLASK_DEBUG` | Flask debug mode | `false` |
| `SYSLOG_HOST` | Syslog server hostname | Not configured |
| `SYSLOG_PORT` | Syslog server port | `514` |
| `APP_HOST` | Application bind address | `0.0.0.0` |
| `APP_PORT` | Application port | `5000` |

## Deployment Architecture

### GitHub Actions CI/CD Pipeline

The application uses GitHub Actions for automated deployment:

1. **Trigger**: Push to `main` branch
2. **Tests**: Runs pytest test suite
3. **Build**: Creates multi-architecture Docker image
4. **Registry**: Pushes to GitHub Container Registry (ghcr.io)
5. **Deploy**: Updates production environment via SSH
6. **Health Check**: Verifies application startup
7. **Rollback**: Automatic rollback on failure

### GitHub Secrets Required

Configure these secrets in the GitHub repository settings:

| Secret Name | Description | Source |
|-------------|-------------|---------|
| `SSH_PRIVATE_KEY` | SSH key for production server access | Generated SSH key pair |
| `POSTGRES_PASSWORD` | Database password | DevOps managed |
| `SECRET_KEY` | Flask application secret | Generated token |
| `SWITCH_USERNAME` | Network device username | Network team |
| `SWITCH_PASSWORD` | Network device password | Network team |

### Production Server Requirements

#### System Requirements
- Docker and Docker Compose installed
- SSH access for deployment user
- PostgreSQL database (can be containerized or external)
- Network access to target switches
- Minimum 2GB RAM, 10GB disk space

#### Directory Structure
```
/opt/dell-port-tracer/
├── docker-compose.yml
├── .env                    # Created by DevOps team
├── logs/
└── data/                   # PostgreSQL data volume
```

#### Database Setup
1. Create PostgreSQL database: `dell_port_tracer`
2. Create user with appropriate permissions
3. Database schema will be created automatically on first run

## Deployment Process

### Initial Setup
1. Clone repository to production server
2. Create `.env` file using `.env.example` as template
3. Configure GitHub secrets
4. Run initial deployment

### Ongoing Deployments
- Deployments are automated via GitHub Actions
- Monitor via GitHub Actions dashboard
- Logs available in production server: `docker logs dell-port-tracer-app`

### Monitoring & Health Checks
- Application health endpoint: `http://server:port/health`
- Database connectivity verified automatically
- Container logs: `docker logs -f dell-port-tracer-app`

## Security Considerations

### Environment Variables
- **Never commit `.env` files** to version control
- Use GitHub Secrets for CI/CD pipeline
- Rotate secrets regularly
- Use strong, unique passwords

### Network Security
- Application runs on internal port 5000
- Use reverse proxy (nginx) for SSL termination
- Firewall rules for database access
- VPN/private network for switch access

### Database Security
- Use dedicated database user with minimal permissions
- Enable SSL connections if database is remote
- Regular backups and testing restore procedures

## Troubleshooting

### Common Issues
1. **Database Connection**: Check `DATABASE_URL` format and credentials
2. **Switch Access**: Verify network connectivity and credentials
3. **Permission Errors**: Ensure Docker has proper permissions
4. **Port Conflicts**: Check if port 5000 is available

### Log Locations
- Application logs: `docker logs dell-port-tracer-app`
- Database logs: `docker logs dell-port-tracer-db`
- System logs: `/var/log/docker/`

## Support Contacts

- **Application Issues**: Development Team
- **Infrastructure**: DevOps Team  
- **Network Access**: Network Team
- **Database**: Database Team

## Change Management

All production changes should go through:
1. Code review and approval
2. Testing in staging environment
3. Deployment during maintenance window
4. Post-deployment verification
5. Rollback plan ready if needed
