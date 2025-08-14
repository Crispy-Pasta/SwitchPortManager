#!/bin/bash

# Dell Switch Port Tracer v2.1.1 - Deployment Script
# This script builds the Docker image and deploys to Kubernetes
# Features: Enhanced UI/UX, VLAN Management v2, Database-driven architecture
# UI Improvements: Dropdown width optimization, VLAN naming conventions

set -e

# Configuration
APP_NAME="dell-port-tracer"
IMAGE_NAME="dell-port-tracer"
IMAGE_TAG="latest"
REGISTRY_PREFIX=""  # Set this to your registry prefix if needed
NAMESPACE="default"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
check_docker() {
    log_info "Checking Docker..."
    if ! docker info &>/dev/null; then
        log_error "Docker is not running. Please start Docker and try again."
        exit 1
    fi
    log_success "Docker is running"
}

# Check if kubectl is available and connected
check_kubectl() {
    log_info "Checking kubectl..."
    if ! command -v kubectl &>/dev/null; then
        log_error "kubectl is not installed. Please install kubectl and try again."
        exit 1
    fi
    
    if ! kubectl cluster-info &>/dev/null; then
        log_error "kubectl is not connected to a cluster. Please configure kubectl and try again."
        exit 1
    fi
    log_success "kubectl is configured and connected"
}

# Build Docker image
build_image() {
    log_info "Building Docker image..."
    
    # Check if database configuration exists
    if [[ ! -f ".env" ]]; then
        log_warning ".env file not found. Using default database configuration."
        log_info "Make sure PostgreSQL database is configured properly."
    fi
    
    # Build the image
    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .
    
    if [[ $? -eq 0 ]]; then
        log_success "Docker image built successfully: ${IMAGE_NAME}:${IMAGE_TAG}"
    else
        log_error "Failed to build Docker image"
        exit 1
    fi
}

# Update ConfigMap with current switches.json
update_configmap() {
    log_info "Updating ConfigMap with switches configuration..."
    
    # Create ConfigMap from switches.json
    kubectl create configmap port-tracer-config \
        --from-file=switches.json=switches.json \
        --dry-run=client -o yaml | kubectl apply -f -
    
    if [[ $? -eq 0 ]]; then
        log_success "ConfigMap updated successfully"
    else
        log_error "Failed to update ConfigMap"
        exit 1
    fi
}

# Deploy to Kubernetes
deploy_to_k8s() {
    log_info "Deploying to Kubernetes..."
    
    # Apply Kubernetes manifests
    kubectl apply -f k8s-secret.yaml
    kubectl apply -f k8s-deployment.yaml
    kubectl apply -f k8s-service.yaml
    
    # Check if deployment was successful
    log_info "Waiting for deployment to be ready..."
    kubectl rollout status deployment/${APP_NAME} --namespace=${NAMESPACE} --timeout=300s
    
    if [[ $? -eq 0 ]]; then
        log_success "Deployment successful!"
        
        # Get service information
        log_info "Service Information:"
        kubectl get services -l app=${APP_NAME} --namespace=${NAMESPACE}
        
        # Get pod information
        log_info "Pod Information:"
        kubectl get pods -l app=${APP_NAME} --namespace=${NAMESPACE}
        
        # Get ingress information if available
        if kubectl get ingress dell-port-tracer-ingress --namespace=${NAMESPACE} &>/dev/null; then
            log_info "Ingress Information:"
            kubectl get ingress dell-port-tracer-ingress --namespace=${NAMESPACE}
        fi
        
    else
        log_error "Deployment failed"
        exit 1
    fi
}

# Show deployment status
show_status() {
    log_info "Current deployment status:"
    kubectl get all -l app=${APP_NAME} --namespace=${NAMESPACE}
    
    log_info "Application logs (latest 20 lines):"
    kubectl logs -l app=${APP_NAME} --namespace=${NAMESPACE} --tail=20
}

# Main deployment function
main() {
    log_info "Starting deployment of Dell Switch Port Tracer..."
    
    # Check prerequisites
    check_docker
    check_kubectl
    
    # Build and deploy
    build_image
    update_configmap
    deploy_to_k8s
    
    log_success "Deployment completed successfully!"
    log_info "You can access the application via:"
    log_info "- NodePort: http://<node-ip>:30080"
    log_info "- Port Forward: kubectl port-forward service/${APP_NAME}-service 8080:80"
    log_info "- Ingress: http://port-tracer.yourdomain.com (if configured)"
    
    # Show final status
    show_status
}

# Handle command line arguments
case "${1:-deploy}" in
    "build")
        check_docker
        build_image
        ;;
    "deploy")
        main
        ;;
    "status")
        check_kubectl
        show_status
        ;;
    "clean")
        log_info "Cleaning up deployment..."
        kubectl delete -f k8s-deployment.yaml --ignore-not-found=true
        kubectl delete -f k8s-service.yaml --ignore-not-found=true
        kubectl delete -f k8s-secret.yaml --ignore-not-found=true
        kubectl delete configmap port-tracer-config --ignore-not-found=true
        log_success "Cleanup completed"
        ;;
    *)
        echo "Usage: $0 {build|deploy|status|clean}"
        echo "  build  - Build Docker image only"
        echo "  deploy - Build and deploy to Kubernetes (default)"
        echo "  status - Show deployment status"
        echo "  clean  - Remove deployment from Kubernetes"
        exit 1
        ;;
esac
