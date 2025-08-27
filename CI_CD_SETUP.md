# CI/CD Setup - Separated Workflows

## 🏗️ Architecture Overview

Following DevOps best practices, we've separated CI and CD into two distinct workflows:

### 1. **CI Pipeline** (`deploy.yml`)
- **Trigger**: Push/PR to main/develop branches  
- **Purpose**: Test code quality and build Docker images
- **Actions**: Tests → Lint → Build → Push to Registry
- **No deployment** - purely for validation

### 2. **CD Pipeline** (`deploy-prod.yml`) 
- **Trigger**: Manual dispatch or successful CI completion
- **Purpose**: Deploy validated images to production
- **Actions**: SSH deploy → Health checks → Rollback on failure
- **DevOps managed** - requires production environment setup

## 📋 Simplified CI Workflow Features

✅ **Clean & Short**: Using repository actions instead of manual commands
✅ **Pip Caching**: Faster dependency installation 
✅ **Combined Steps**: Merged related operations
✅ **Focused Scope**: Only CI concerns (test, lint, build)
✅ **DevOps Friendly**: Easy to understand and maintain

## 🔄 Workflow Separation Benefits

### CI Pipeline (Always Runs)
```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
```

### CD Pipeline (DevOps Controlled)
```yaml
on:
  workflow_run:
    workflows: ["🔍 CI - Test and Build"]
    types: [completed]
    branches: [main]
  workflow_dispatch: # Manual trigger
```

## 🚀 Usage

### For Developers:
1. Push code → CI runs automatically
2. All tests must pass + linting clean
3. Docker image built and pushed to registry
4. **No automatic deployment**

### For DevOps:
1. Monitor CI success in GitHub Actions
2. Manually trigger CD when ready:
   - Go to Actions → CD - Deploy to Production 
   - Click "Run workflow"
   - Choose image tag (default: latest)
3. Monitor deployment progress and health checks

## 🛠️ Local Testing

```bash
# Run the same tests locally
pytest tests/ -v --tb=short --cov=. --cov-report=xml

# Run linting
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Build Docker image locally
docker build -t port-tracer:local .
```

## 📊 Monitoring

- **CI Status**: GitHub Actions tab → CI workflows
- **Image Registry**: GitHub Packages → Container registry
- **Production Health**: `curl https://your-domain/health`

## 🔒 Security

- **Environment Variables**: Managed by DevOps team
- **GitHub Secrets**: SSH keys, credentials stored securely  
- **Production Access**: Restricted to authorized workflows
- **Image Signing**: Docker images tagged and versioned

This approach gives developers fast feedback while giving DevOps full control over production deployments.
