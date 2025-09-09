# Docker Compose Configurations

## Available Configurations

The Dell Switch Port Tracer provides **two Docker Compose configurations** for different deployment scenarios:

### 1. Development Setup (`docker-compose.yml`)
- **Purpose**: Local development and testing
- **Services**: Application + PostgreSQL database
- **Port**: 5000 (direct Flask access)
- **Usage**: 
  ```bash
  docker-compose up -d
  ```
- **Best for**: Developers working on the application locally

### 2. Production App-Only (`docker-compose.prod-minimal.yml`)
- **Purpose**: Production deployment with existing infrastructure
- **Services**: Application container only
- **Port**: 5000 (for nginx proxy)
- **Requirements**: 
  - Existing PostgreSQL database
  - Existing nginx reverse proxy
- **Usage**:
  ```bash
  # Copy and configure environment
  cp .env.prod-minimal.example .env
  # Edit .env with your database credentials and settings
  
  # Deploy only the application
  docker-compose -f docker-compose.prod-minimal.yml up -d
  ```
- **Best for**: Production deployments where DevOps team manages nginx and database separately

## Environment Configuration

### Development
Use the default `.env` file or the provided `.env.example`

### Production (App-Only)
Use `.env.prod-minimal.example` as template:
```bash
cp .env.prod-minimal.example .env
```

Edit the `.env` file with your production values:
- Database connection details (existing PostgreSQL)
- Application secrets and passwords
- Switch credentials
- Performance settings

## Production Nginx Configuration

When using `docker-compose.prod-minimal.yml`, configure your existing nginx to proxy to the application:

```nginx
upstream dell_port_tracer {
    server 127.0.0.1:5000;
    keepalive 32;
}

location / {
    proxy_pass http://dell_port_tracer;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
}
```

## Data Persistence

- **Development**: Uses Docker named volume `postgres_data`
- **Production**: Relies on your existing PostgreSQL instance for data persistence
- **Logs**: Both configurations mount `./logs` for application logs
- **Backups**: Both configurations mount `./backups` for database backups
