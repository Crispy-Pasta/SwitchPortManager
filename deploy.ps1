# Dell Switch Port Tracer - PowerShell Deployment Script
# This script builds the Docker image and deploys to Kubernetes

param(
    [Parameter(Position=0)]
    [ValidateSet("build", "deploy", "status", "clean")]
    [string]$Action = "deploy"
)

# Configuration
$APP_NAME = "dell-port-tracer"
$IMAGE_NAME = "dell-port-tracer"
$IMAGE_TAG = "latest"
$NAMESPACE = "default"

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Cyan"

# Functions
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $Red
}

# Check if Docker is running
function Test-Docker {
    Write-Info "Checking Docker..."
    try {
        $null = docker info 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Docker is running"
            return $true
        }
    }
    catch {
        Write-Error "Docker is not running. Please start Docker and try again."
        return $false
    }
    Write-Error "Docker is not running. Please start Docker and try again."
    return $false
}

# Check if kubectl is available and connected
function Test-Kubectl {
    Write-Info "Checking kubectl..."
    
    if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
        Write-Error "kubectl is not installed. Please install kubectl and try again."
        return $false
    }
    
    try {
        $null = kubectl cluster-info 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "kubectl is configured and connected"
            return $true
        }
    }
    catch {
        Write-Error "kubectl is not connected to a cluster. Please configure kubectl and try again."
        return $false
    }
    Write-Error "kubectl is not connected to a cluster. Please configure kubectl and try again."
    return $false
}

# Build Docker image
function Build-Image {
    Write-Info "Building Docker image..."
    
    # Check if switches.json exists
    if (-not (Test-Path "switches.json")) {
        Write-Error "switches.json not found. Please ensure the switches configuration file exists."
        return $false
    }
    
    # Build the image
    docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" .
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker image built successfully: ${IMAGE_NAME}:${IMAGE_TAG}"
        return $true
    } else {
        Write-Error "Failed to build Docker image"
        return $false
    }
}

# Update ConfigMap with current switches.json
function Update-ConfigMap {
    Write-Info "Updating ConfigMap with switches configuration..."
    
    # Create ConfigMap from switches.json
    $configMapYaml = kubectl create configmap port-tracer-config --from-file=switches.json=switches.json --dry-run=client -o yaml
    $configMapYaml | kubectl apply -f -
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "ConfigMap updated successfully"
        return $true
    } else {
        Write-Error "Failed to update ConfigMap"
        return $false
    }
}

# Deploy to Kubernetes
function Deploy-ToK8s {
    Write-Info "Deploying to Kubernetes..."
    
    # Apply Kubernetes manifests
    kubectl apply -f k8s-secret.yaml
    kubectl apply -f k8s-deployment.yaml
    kubectl apply -f k8s-service.yaml
    
    # Check if deployment was successful
    Write-Info "Waiting for deployment to be ready..."
    kubectl rollout status deployment/$APP_NAME --namespace=$NAMESPACE --timeout=300s
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Deployment successful!"
        
        # Get service information
        Write-Info "Service Information:"
        kubectl get services -l app=$APP_NAME --namespace=$NAMESPACE
        
        # Get pod information
        Write-Info "Pod Information:"
        kubectl get pods -l app=$APP_NAME --namespace=$NAMESPACE
        
        # Get ingress information if available
        $ingressExists = kubectl get ingress dell-port-tracer-ingress --namespace=$NAMESPACE 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Ingress Information:"
            kubectl get ingress dell-port-tracer-ingress --namespace=$NAMESPACE
        }
        
        return $true
    } else {
        Write-Error "Deployment failed"
        return $false
    }
}

# Show deployment status
function Show-Status {
    Write-Info "Current deployment status:"
    kubectl get all -l app=$APP_NAME --namespace=$NAMESPACE
    
    Write-Info "Application logs (latest 20 lines):"
    kubectl logs -l app=$APP_NAME --namespace=$NAMESPACE --tail=20
}

# Main deployment function
function Start-Deployment {
    Write-Info "Starting deployment of Dell Switch Port Tracer..."
    
    # Check prerequisites
    if (-not (Test-Docker)) { return }
    if (-not (Test-Kubectl)) { return }
    
    # Build and deploy
    if (-not (Build-Image)) { return }
    if (-not (Update-ConfigMap)) { return }
    if (-not (Deploy-ToK8s)) { return }
    
    Write-Success "Deployment completed successfully!"
    Write-Info "You can access the application via:"
    Write-Info "- NodePort: http://<node-ip>:30080"
    Write-Info "- Port Forward: kubectl port-forward service/$APP_NAME-service 8080:80"
    Write-Info "- Ingress: http://port-tracer.yourdomain.com (if configured)"
    
    # Show final status
    Show-Status
}

# Clean up deployment
function Remove-Deployment {
    Write-Info "Cleaning up deployment..."
    kubectl delete -f k8s-deployment.yaml --ignore-not-found=true
    kubectl delete -f k8s-service.yaml --ignore-not-found=true
    kubectl delete -f k8s-secret.yaml --ignore-not-found=true
    kubectl delete configmap port-tracer-config --ignore-not-found=true
    Write-Success "Cleanup completed"
}

# Main script logic
switch ($Action) {
    "build" {
        if (Test-Docker) {
            Build-Image
        }
    }
    "deploy" {
        Start-Deployment
    }
    "status" {
        if (Test-Kubectl) {
            Show-Status
        }
    }
    "clean" {
        Remove-Deployment
    }
    default {
        Write-Host "Usage: .\deploy.ps1 {build|deploy|status|clean}"
        Write-Host "  build  - Build Docker image only"
        Write-Host "  deploy - Build and deploy to Kubernetes (default)"
        Write-Host "  status - Show deployment status"
        Write-Host "  clean  - Remove deployment from Kubernetes"
    }
}
