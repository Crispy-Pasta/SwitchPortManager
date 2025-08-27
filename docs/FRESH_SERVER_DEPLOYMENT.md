# Fresh Server Deployment Strategies - Dell Switch Port Tracer v2.1.6

## 🎯 **Deployment Approaches for Fresh Servers**

Since we disabled the CD pipeline, here are modern deployment approaches for fresh server installations:

## 🚀 **Approach 1: Docker Pull & Compose (Recommended)**

### **Simple Production Deployment**
```bash
# On fresh server
# 1. Install Docker & Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 2. Create deployment directory
sudo mkdir -p /opt/dell-port-tracer
cd /opt/dell-port-tracer

# 3. Download production docker-compose file
curl -o docker-compose.yml https://raw.githubusercontent.com/Crispy-Pasta/SwitchPortManager/main/docker-compose.prod.yml

# 4. Create environment file
cat > .env << 'EOF'
# Database Configuration
POSTGRES_DB=port_tracer_db
POSTGRES_USER=dell_tracer_user
POSTGRES_PASSWORD=YOUR_SECURE_PASSWORD_HERE
DATABASE_URL=postgresql://dell_tracer_user:YOUR_SECURE_PASSWORD_HERE@postgres:5432/port_tracer_db

# Application Security
SECRET_KEY=YOUR_GENERATED_SECRET_KEY_HERE
SESSION_COOKIE_SECURE=true  # Set to true for HTTPS
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Strict

# Switch Credentials
SWITCH_USERNAME=your_switch_username
SWITCH_PASSWORD=your_switch_password

# User Passwords
WEB_PASSWORD=your_admin_password
NETADMIN_PASSWORD=your_netadmin_password
SUPERADMIN_PASSWORD=your_superadmin_password
EOF

# 5. Deploy with specific version
docker-compose up -d
```

### **Advantages:**
- ✅ Uses fresh Docker images from registry
- ✅ No source code needed on server
- ✅ Automatic database initialization
- ✅ Version-controlled deployment
- ✅ Easy rollback capabilities

---

## 🔧 **Approach 2: Infrastructure as Code**

### **Using Ansible**
Create an Ansible playbook for automated deployment:

```yaml
# deploy-port-tracer.yml
- hosts: target_servers
  become: yes
  vars:
    app_version: "v2.1.6"
    docker_image: "ghcr.io/crispy-pasta/port-tracer:latest"
    
  tasks:
    - name: Install Docker
      shell: curl -fsSL https://get.docker.com | sh
      
    - name: Install Docker Compose
      get_url:
        url: "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-Linux-x86_64"
        dest: /usr/local/bin/docker-compose
        mode: '0755'
        
    - name: Create application directory
      file:
        path: /opt/dell-port-tracer
        state: directory
        
    - name: Deploy docker-compose.yml
      template:
        src: docker-compose.prod.yml.j2
        dest: /opt/dell-port-tracer/docker-compose.yml
        
    - name: Deploy environment file
      template:
        src: .env.j2
        dest: /opt/dell-port-tracer/.env
        mode: '0600'
        
    - name: Pull latest Docker image
      shell: docker pull {{ docker_image }}
      
    - name: Deploy application
      shell: cd /opt/dell-port-tracer && docker-compose up -d
      
    - name: Verify deployment
      uri:
        url: http://localhost:5000/health
        method: GET
```

**Deploy:**
```bash
ansible-playbook -i inventory deploy-port-tracer.yml
```

---

## 🌐 **Approach 3: Cloud-Native Deployment**

### **Using Kubernetes**
```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: port-tracer
spec:
  replicas: 2
  selector:
    matchLabels:
      app: port-tracer
  template:
    metadata:
      labels:
        app: port-tracer
    spec:
      containers:
      - name: port-tracer
        image: ghcr.io/crispy-pasta/port-tracer:latest
        ports:
        - containerPort: 5000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: port-tracer-secrets
              key: database-url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: port-tracer-secrets
              key: secret-key
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        resources:
          limits:
            memory: "1Gi"
            cpu: "1000m"
          requests:
            memory: "256Mi"
            cpu: "250m"
---
apiVersion: v1
kind: Service
metadata:
  name: port-tracer-service
spec:
  selector:
    app: port-tracer
  ports:
  - port: 80
    targetPort: 5000
  type: LoadBalancer
```

**Deploy:**
```bash
kubectl apply -f k8s-deployment.yaml
```

---

## 📦 **Approach 4: Single-Server Deployment Script**

### **Automated Deployment Script**
```bash
#!/bin/bash
# deploy-fresh-server.sh

set -e

APP_VERSION=${1:-"latest"}
INSTALL_DIR="/opt/dell-port-tracer"
DOCKER_IMAGE="ghcr.io/crispy-pasta/port-tracer:${APP_VERSION}"

echo "🚀 Deploying Dell Port Tracer v${APP_VERSION} to fresh server..."

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    sudo systemctl start docker
    sudo systemctl enable docker
    sudo usermod -aG docker $USER
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Create directories
echo "📁 Creating application directories..."
sudo mkdir -p ${INSTALL_DIR}/{logs,backups,data}
cd ${INSTALL_DIR}

# Download deployment files
echo "⬇️ Downloading deployment files..."
curl -o docker-compose.yml https://raw.githubusercontent.com/Crispy-Pasta/SwitchPortManager/main/docker-compose.prod.yml
curl -o .env.example https://raw.githubusercontent.com/Crispy-Pasta/SwitchPortManager/main/.env.example

# Setup environment
if [ ! -f .env ]; then
    echo "⚙️ Creating environment configuration..."
    cp .env.example .env
    
    # Generate secure secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/your_generated_secret_key/${SECRET_KEY}/g" .env
    
    echo "⚠️  IMPORTANT: Edit .env file with your specific configuration!"
    echo "   - Database passwords"
    echo "   - Switch credentials" 
    echo "   - User passwords"
    echo ""
fi

# Pull latest image
echo "🐳 Pulling Docker image: ${DOCKER_IMAGE}..."
docker pull ${DOCKER_IMAGE}

# Deploy application
echo "🚀 Deploying application..."
docker-compose up -d

# Wait for health check
echo "⏳ Waiting for application to start..."
sleep 30

# Verify deployment
if curl -f http://localhost:5000/health &> /dev/null; then
    echo "✅ Deployment successful!"
    echo "🌐 Application available at: http://$(hostname -I | awk '{print $1}'):5000"
    echo "👤 Default login: admin / password (change in .env file)"
else
    echo "❌ Deployment failed - check logs:"
    docker-compose logs
    exit 1
fi

echo "🎉 Dell Port Tracer deployed successfully!"
```

**Usage:**
```bash
# Deploy latest version
curl -o deploy.sh https://raw.githubusercontent.com/Crispy-Pasta/SwitchPortManager/main/deploy-fresh-server.sh
chmod +x deploy.sh
sudo ./deploy.sh

# Deploy specific version
sudo ./deploy.sh v2.1.6
```

---

## 🔄 **Approach 5: GitOps with ArgoCD**

### **Using ArgoCD for Kubernetes**
```yaml
# argocd-application.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: port-tracer
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/Crispy-Pasta/SwitchPortManager
    targetRevision: main
    path: k8s/
  destination:
    server: https://kubernetes.default.svc
    namespace: port-tracer
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

---

## 🏭 **Approach 6: Cloud Platform Deployment**

### **Using Cloud Services**

#### **AWS ECS**
```bash
# Create ECS task definition and service
aws ecs create-task-definition \
  --family port-tracer \
  --container-definitions '[{
    "name": "port-tracer",
    "image": "ghcr.io/crispy-pasta/port-tracer:latest",
    "memory": 1024,
    "portMappings": [{
      "containerPort": 5000,
      "protocol": "tcp"
    }]
  }]'
```

#### **Azure Container Instances**
```bash
az container create \
  --resource-group myResourceGroup \
  --name port-tracer \
  --image ghcr.io/crispy-pasta/port-tracer:latest \
  --ports 5000 \
  --environment-variables DATABASE_URL="postgresql://..." \
  --secure-environment-variables SECRET_KEY="..."
```

#### **Google Cloud Run**
```bash
gcloud run deploy port-tracer \
  --image ghcr.io/crispy-pasta/port-tracer:latest \
  --platform managed \
  --port 5000 \
  --set-env-vars DATABASE_URL="postgresql://..."
```

---

## 🎯 **Recommended Approach by Use Case**

| Use Case | Recommended Approach | Why |
|----------|---------------------|-----|
| **Single Production Server** | Docker Pull & Compose | Simple, reliable, easy maintenance |
| **Multiple Servers** | Ansible Automation | Consistent deployment, infrastructure as code |
| **Container Platform** | Kubernetes + Helm | Scalable, cloud-native, auto-scaling |
| **Cloud Environment** | Cloud-specific services | Managed infrastructure, built-in monitoring |
| **Development/Testing** | Deployment Script | Quick setup, easy cleanup |
| **Enterprise GitOps** | ArgoCD + Kubernetes | Automated, auditable, rollback capabilities |

---

## 🛠️ **Next Steps**

1. **Choose your preferred approach** based on infrastructure
2. **Prepare environment variables** (database, switch credentials)
3. **Test deployment** in non-production environment first
4. **Monitor deployment** using health checks and logs
5. **Set up backup strategy** for database and configuration

Which deployment approach interests you most for your fresh server setup? I can provide detailed implementation steps for your specific scenario!
