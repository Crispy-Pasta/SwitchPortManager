# Dell Switch Port Tracer - Kubernetes Deployment Guide

This guide explains how to deploy the Dell Switch Port Tracer application to a Kubernetes cluster using Docker containers.

## 📋 Prerequisites

### Required Software
- **Docker** (version 20.10 or later)
- **Kubernetes cluster** (version 1.19 or later)
- **kubectl** configured to connect to your cluster
- **bash** shell (for deployment scripts)

### Optional Software
- **NGINX Ingress Controller** (for external access via domain name)
- **cert-manager** (for automatic SSL certificates)

## 🏗️ Architecture Overview

The application is deployed with the following components:

- **Deployment**: Runs 2 replicas of the application for high availability
- **ConfigMap**: Stores the switches configuration
- **Secret**: Stores sensitive credentials (passwords, API keys)
- **Service**: Provides internal load balancing and service discovery
- **Ingress**: (Optional) Provides external access via domain name

## 🚀 Quick Start

### 1. Build and Deploy (Automated)

```bash
# Make the deployment script executable
chmod +x deploy.sh

# Deploy everything (build image + deploy to Kubernetes)
./deploy.sh deploy
```

### 2. Access the Application

After deployment, you can access the application via:

- **NodePort**: `http://<node-ip>:30080`
- **Port Forward**: `kubectl port-forward service/dell-port-tracer-service 8080:80`
- **Ingress**: `http://port-tracer.yourdomain.com` (if configured)

## 📝 Manual Deployment Steps

### Step 1: Update Configuration

#### Update Secrets
Edit `k8s-secret.yaml` and update the base64-encoded values:

```bash
# Example: Encode your switch username
echo -n 'your_switch_username' | base64

# Example: Encode your switch password
echo -n 'your_switch_password' | base64
```

#### Update Switches Configuration
Ensure your `switches.json` file contains your actual switch configuration.

### Step 2: Build Docker Image

```bash
# Build the Docker image
docker build -t dell-port-tracer:latest .

# Verify the image was built
docker images | grep dell-port-tracer
```

### Step 3: Deploy to Kubernetes

```bash
# Create the secret (update with your credentials first)
kubectl apply -f k8s-secret.yaml

# Create the ConfigMap from your switches.json
kubectl create configmap port-tracer-config --from-file=switches.json=switches.json

# Deploy the application
kubectl apply -f k8s-deployment.yaml

# Create the service
kubectl apply -f k8s-service.yaml

# (Optional) Create the ingress
kubectl apply -f k8s-ingress.yaml
```

### Step 4: Verify Deployment

```bash
# Check deployment status
kubectl get deployments

# Check pods
kubectl get pods -l app=dell-port-tracer

# Check services
kubectl get services -l app=dell-port-tracer

# Check application logs
kubectl logs -l app=dell-port-tracer
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `USE_WINDOWS_AUTH` | Enable Windows/AD authentication | `false` | No |
| `SWITCH_USERNAME` | SSH username for switches | - | Yes |
| `SWITCH_PASSWORD` | SSH password for switches | - | Yes |
| `OSS_PASSWORD` | Password for OSS user | `oss123` | No |
| `NETADMIN_PASSWORD` | Password for NetAdmin user | `netadmin123` | No |
| `SUPERADMIN_PASSWORD` | Password for SuperAdmin user | `superadmin123` | No |
| `AD_SERVER` | Active Directory server URL | - | No |
| `AD_DOMAIN` | Active Directory domain | - | No |
| `AD_BASE_DN` | Active Directory base DN | - | No |

### Resource Requirements

**Minimum:**
- CPU: 250m
- Memory: 256Mi

**Recommended:**
- CPU: 500m
- Memory: 512Mi

### Storage

- **ConfigMap**: Stores switch configuration (read-only)
- **EmptyDir**: Stores application logs (ephemeral)

## 🔒 Security Features

### Container Security
- Runs as non-root user (UID 1000)
- Read-only root filesystem where possible
- Drops all capabilities
- No privilege escalation

### Network Security
- ClusterIP service for internal communication
- Optional TLS termination at ingress
- Session affinity for login consistency

### Secrets Management
- Credentials stored in Kubernetes Secrets
- Base64 encoding (consider using external secret management)

## 📊 Monitoring and Health Checks

### Health Endpoints
- **Liveness Probe**: `GET /health` (checks application health)
- **Readiness Probe**: `GET /health` (checks if ready to serve traffic)

### Monitoring

```bash
# Check application health
kubectl get pods -l app=dell-port-tracer

# View application logs
kubectl logs -l app=dell-port-tracer -f

# Check resource usage
kubectl top pods -l app=dell-port-tracer
```

## 🔄 Maintenance Operations

### Update Switches Configuration

```bash
# Update the ConfigMap with new switches.json
kubectl create configmap port-tracer-config \
    --from-file=switches.json=switches.json \
    --dry-run=client -o yaml | kubectl apply -f -

# Restart pods to pick up new configuration
kubectl rollout restart deployment/dell-port-tracer
```

### Update Application

```bash
# Build new image
docker build -t dell-port-tracer:v1.1.0 .

# Update deployment with new image
kubectl set image deployment/dell-port-tracer port-tracer=dell-port-tracer:v1.1.0

# Check rollout status
kubectl rollout status deployment/dell-port-tracer
```

### Scale Application

```bash
# Scale to 3 replicas
kubectl scale deployment dell-port-tracer --replicas=3

# Verify scaling
kubectl get pods -l app=dell-port-tracer
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Pods Not Starting
```bash
# Check pod status
kubectl describe pods -l app=dell-port-tracer

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp
```

#### 2. Health Check Failures
```bash
# Check application logs
kubectl logs -l app=dell-port-tracer --tail=50

# Test health endpoint manually
kubectl port-forward service/dell-port-tracer-service 8080:80
curl http://localhost:8080/health
```

#### 3. Configuration Issues
```bash
# Check ConfigMap
kubectl describe configmap port-tracer-config

# Check Secret
kubectl describe secret port-tracer-secrets
```

### Useful Commands

```bash
# Get all resources
kubectl get all -l app=dell-port-tracer

# Delete everything
./deploy.sh clean

# Check logs from all pods
kubectl logs -l app=dell-port-tracer --prefix=true

# Execute shell in pod
kubectl exec -it deployment/dell-port-tracer -- /bin/bash
```

## 🌐 External Access Options

### Option 1: NodePort (Simple)
The application is available on port 30080 of any cluster node.

### Option 2: Port Forward (Development)
```bash
kubectl port-forward service/dell-port-tracer-service 8080:80
# Access at http://localhost:8080
```

### Option 3: Ingress (Production)
Configure DNS to point to your ingress controller and update the ingress hostname.

## 📈 Production Considerations

### High Availability
- Use multiple replicas (minimum 2)
- Deploy across multiple availability zones
- Use pod disruption budgets

### Performance
- Monitor resource usage and adjust limits
- Consider horizontal pod autoscaling
- Use persistent volumes for logs if needed

### Security
- Use external secret management (Vault, Azure Key Vault, etc.)
- Enable network policies
- Regular security updates

### Backup
- Backup switches configuration regularly
- Export audit logs periodically
- Document configuration changes

## 📞 Support

For issues and questions:
1. Check the application logs
2. Review Kubernetes events
3. Consult the main application documentation
4. Contact the Network Operations Team
