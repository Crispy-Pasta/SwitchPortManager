#!/bin/bash
# Dell Port Tracer - Fresh Server Deployment Script
# Version: 2.1.6
# Usage: ./deploy-fresh-server.sh [version]

set -e

APP_VERSION=${1:-"latest"}
INSTALL_DIR="/opt/dell-port-tracer"
DOCKER_IMAGE="ghcr.io/crispy-pasta/port-tracer:${APP_VERSION}"

echo "🚀 Deploying Dell Port Tracer v${APP_VERSION} to fresh server..."
echo "📍 Installation directory: ${INSTALL_DIR}"
echo "🐳 Docker image: ${DOCKER_IMAGE}"
echo ""

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root or with sudo"
    echo "   Usage: sudo ./deploy-fresh-server.sh [version]"
    exit 1
fi

# Install Docker
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl start docker
    systemctl enable docker
    echo "✅ Docker installed successfully"
else
    echo "✅ Docker already installed"
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.21.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose installed successfully"
else
    echo "✅ Docker Compose already installed"
fi

# Create directories
echo "📁 Creating application directories..."
mkdir -p ${INSTALL_DIR}/{logs,backups,data}
cd ${INSTALL_DIR}
echo "✅ Directories created: ${INSTALL_DIR}"

# Download deployment files
echo "⬇️ Downloading deployment files from GitHub..."
curl -o docker-compose.yml https://raw.githubusercontent.com/Crispy-Pasta/SwitchPortManager/main/docker-compose.prod.yml
if [ $? -eq 0 ]; then
    echo "✅ Downloaded docker-compose.yml"
else
    echo "❌ Failed to download docker-compose.yml"
    exit 1
fi

curl -o .env.example https://raw.githubusercontent.com/Crispy-Pasta/SwitchPortManager/main/.env.example  
if [ $? -eq 0 ]; then
    echo "✅ Downloaded .env.example"
else
    echo "❌ Failed to download .env.example"
    exit 1
fi

# Setup environment file
if [ ! -f .env ]; then
    echo "⚙️ Creating environment configuration..."
    cp .env.example .env
    
    # Generate secure secret key
    if command -v python3 &> /dev/null; then
        SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
        sed -i "s/your_generated_secret_key_here/${SECRET_KEY}/g" .env
        echo "✅ Generated secure SECRET_KEY"
    else
        echo "⚠️  Python3 not found - you'll need to manually set SECRET_KEY in .env"
    fi
    
    # Generate secure database password
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    sed -i "s/YOUR_SECURE_DATABASE_PASSWORD/${DB_PASSWORD}/g" .env
    echo "✅ Generated secure database password"
    
    echo ""
    echo "⚠️  IMPORTANT: Edit ${INSTALL_DIR}/.env file with your configuration:"
    echo "   🔑 Switch credentials (SWITCH_USERNAME, SWITCH_PASSWORD)"
    echo "   👤 User passwords (WEB_PASSWORD, NETADMIN_PASSWORD, etc.)"
    echo "   🔒 Review security settings for your environment"
    echo ""
else
    echo "✅ Using existing .env file"
fi

# Set proper permissions
chown -R 1000:1000 ${INSTALL_DIR}
chmod 600 .env
echo "✅ Set proper file permissions"

# Pull Docker image
echo "🐳 Pulling Docker image: ${DOCKER_IMAGE}..."
docker pull ${DOCKER_IMAGE}
if [ $? -eq 0 ]; then
    echo "✅ Docker image pulled successfully"
else
    echo "❌ Failed to pull Docker image"
    exit 1
fi

# Deploy application
echo "🚀 Starting Dell Port Tracer..."
docker-compose up -d
if [ $? -eq 0 ]; then
    echo "✅ Application containers started"
else
    echo "❌ Failed to start containers"
    docker-compose logs
    exit 1
fi

# Wait for application startup
echo "⏳ Waiting for application to initialize (60 seconds)..."
sleep 60

# Verify deployment
echo "🔍 Verifying deployment..."
if curl -f http://localhost:5000/health &> /dev/null; then
    echo "✅ Health check passed!"
    echo ""
    echo "🎉 Dell Port Tracer deployed successfully!"
    echo ""
    echo "📍 Application Details:"
    echo "   🌐 URL: http://$(hostname -I | awk '{print $1}'):5000"
    echo "   👤 Default login: admin / password"
    echo "   📁 Installation: ${INSTALL_DIR}"
    echo "   🐳 Image: ${DOCKER_IMAGE}"
    echo ""
    echo "📋 Next Steps:"
    echo "   1. Edit ${INSTALL_DIR}/.env with your switch credentials"
    echo "   2. Change default passwords for security"
    echo "   3. Configure firewall rules if needed"
    echo "   4. Set up HTTPS reverse proxy for production"
    echo ""
    echo "📊 Management Commands:"
    echo "   View logs:    docker-compose -f ${INSTALL_DIR}/docker-compose.yml logs"
    echo "   Restart:      docker-compose -f ${INSTALL_DIR}/docker-compose.yml restart"
    echo "   Stop:         docker-compose -f ${INSTALL_DIR}/docker-compose.yml down"
    echo "   Update:       docker-compose -f ${INSTALL_DIR}/docker-compose.yml pull && docker-compose -f ${INSTALL_DIR}/docker-compose.yml up -d"
else
    echo "❌ Health check failed!"
    echo "📋 Troubleshooting:"
    echo "   Check container status: docker-compose -f ${INSTALL_DIR}/docker-compose.yml ps"
    echo "   View logs: docker-compose -f ${INSTALL_DIR}/docker-compose.yml logs"
    echo "   Check firewall: sudo ufw status"
    exit 1
fi
