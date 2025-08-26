# 🚀 GitHub Actions CI/CD Setup Guide - Step by Step

## Step 1: Generate SSH Key for Production Server

First, let's create a dedicated SSH key for GitHub Actions to access your production server:

### On your local machine:
```powershell
# Generate a new SSH key pair for CI/CD
ssh-keygen -t ed25519 -C "github-actions-porttracer" -f "$env:USERPROFILE\.ssh\github-actions-porttracer"

# Display the public key to copy
Get-Content "$env:USERPROFILE\.ssh\github-actions-porttracer.pub"

# Display the private key to copy (we'll use this in GitHub Secrets)
Get-Content "$env:USERPROFILE\.ssh\github-actions-porttracer"
```

### On your production server (10.50.0.225):
```bash
# Add the public key to authorized_keys
echo "ssh-ed25519 AAAA... github-actions-porttracer" >> ~/.ssh/authorized_keys

# Set proper permissions
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

## Step 2: Configure GitHub Repository Settings

### A. Enable GitHub Container Registry

1. Go to your repository: https://github.com/Crispy-Pasta/SwitchPortManager
2. Click **Settings** tab
3. Scroll down to **Features** section
4. Check ✅ **Packages** (if not already enabled)

### B. Create Environments

1. In repository **Settings** → **Environments**
2. Click **New environment**
3. Name it: `production`
4. Click **Configure environment**
5. **Optional**: Add protection rules:
   - ✅ Required reviewers: (add yourself)
   - ✅ Deployment branches: `main` only

## Step 3: Add Repository Secrets

Go to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add each of these secrets:

### Required Secrets:

**SSH_PRIVATE_KEY**
```
-----BEGIN OPENSSH PRIVATE KEY-----
[Paste the entire private key content from github-actions-porttracer file]
-----END OPENSSH PRIVATE KEY-----
```

**POSTGRES_PASSWORD**
```
secure_password123
```

**SECRET_KEY**
```
[Generate a new secret key - run: python -c "import secrets; print(secrets.token_hex(32))"]
```

**SWITCH_USERNAME**
```
estradajan
```

**SWITCH_PASSWORD**
```
[Your switch password - encrypted in GitHub]
```

### Optional Secrets:

**SYSLOG_SERVER**
```
10.10.250.18
```

**SYSLOG_PORT**
```
514
```

## Step 4: Verify Repository Structure

Your repository should now have these files:
```
├── .github/
│   └── workflows/
│       └── deploy.yml                 ✅ Main CI/CD pipeline
├── Dockerfile.production              ✅ Optimized production build
├── docker-compose.registry.yml        ✅ Registry-based deployment
├── DEPLOYMENT_GUIDE.md               ✅ Complete deployment guide
└── [existing files...]
```

## Step 5: Test the CI/CD Pipeline

### Method 1: Create a Test Branch
```powershell
# Create and push a test branch to trigger the pipeline
git checkout -b feature/test-cicd
git push origin feature/test-cicd

# This will trigger the test job but not deployment
```

### Method 2: Direct Main Push (Production Deployment)
```powershell
# Make a small change to trigger deployment
echo "# CI/CD Pipeline Active" >> README.md
git add README.md
git commit -m "🔧 Test CI/CD pipeline activation"
git push origin main

# This will trigger full pipeline including production deployment
```

## Step 6: Monitor the Deployment

1. Go to **Actions** tab in your GitHub repository
2. You should see a workflow run titled "🚀 Build and Deploy Port Tracer"
3. Click on the run to see detailed logs
4. Monitor each job:
   - 🧪 **Test and Validation**
   - 🐳 **Build Docker Images** 
   - 🚀 **Deploy to Production**

## Step 7: Verify Production Deployment

After the pipeline completes:

```powershell
# Check the new registry-based container
ssh janzen@10.50.0.225 "docker images | grep ghcr.io"

# Verify the application is running
curl http://10.50.0.225:5000/health

# Check container status
ssh janzen@10.50.0.225 "docker ps"
```

## 🚨 Troubleshooting

### Common Issues:

1. **SSH Connection Fails**
   ```bash
   # Test SSH connection manually
   ssh -i ~/.ssh/github-actions-porttracer janzen@10.50.0.225 "echo 'Connection successful'"
   ```

2. **Secrets Not Working**
   - Verify secret names match exactly (case-sensitive)
   - Check for extra spaces or newlines

3. **Docker Registry Authentication**
   - GitHub Actions automatically handles GHCR authentication
   - Verify repository has packages enabled

4. **Build Failures**
   - Check GitHub Actions logs for specific error messages
   - Verify all required files are in the repository

### Getting Help:

- **GitHub Actions Logs**: Repository → Actions tab → Workflow run
- **Production Server Logs**: `ssh janzen@10.50.0.225 "docker logs [container-name]"`
- **Registry Issues**: Check GitHub Packages section

## Next Steps After Setup:

1. **Tag a Release**: `git tag v2.1.6 && git push origin v2.1.6`
2. **Monitor Deployments**: Check Actions tab for deployment history  
3. **Set up Staging**: Modify workflow for develop branch deployments
4. **Add Monitoring**: Integrate with your monitoring systems

---

🎉 **Once these steps are complete, you'll have a fully automated CI/CD pipeline that eliminates all the manual deployment issues we encountered!**
