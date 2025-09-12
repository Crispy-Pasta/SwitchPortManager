# Developer Guide - Version Management

## 🎯 **Version Centralization System**

As of v2.2.0, the Dell Switch Port Tracer uses a centralized version management system to ensure consistency across all components and eliminate version duplication.

## 📍 **Single Source of Truth**

### Primary Version Location
The application version is defined in **ONE place only**:

```python
# app/__init__.py
__version__ = "2.2.0"
```

This is the **only** place where the version should be modified.

## 🛠️ **How to Update the Version**

### Step 1: Update the Version
Edit `app/__init__.py` and change the `__version__` value:

```python
# app/__init__.py
__version__ = "2.2.1"  # Update this line only
```

### Step 2: Verify Version Consistency
Run the version utility to confirm:

```bash
python get_version.py
# Should output: 2.2.1
```

### Step 3: Update Documentation (if needed)
Only update documentation files if they reference specific versions:
- `README.md` (version badge)
- `CHANGELOG.md` (new entry)
- `architecture/README.md` (if referenced)

## 🔧 **Programmatic Version Access**

### Using get_version.py Utility
For scripts and automated processes that need version information:

```bash
# Command line usage
python get_version.py

# In shell scripts
VERSION=$(python get_version.py)
echo "Current version: $VERSION"

# Docker builds
docker build -t app:$(python get_version.py) .

# Git tagging
git tag -a v$(python get_version.py) -m "Release v$(python get_version.py)"
```

### Why get_version.py?
- **No Import Dependencies**: Doesn't require importing the full application
- **Build Safety**: Works even if some dependencies are missing
- **Shell Integration**: Easy to use in bash scripts and CI/CD pipelines
- **Error Handling**: Provides clear error messages if version can't be found

### Python Code Usage
For Python code that needs the version:

```python
# Within the application
from app import __version__
print(f"Running version {__version__}")

# From utilities
from app.core.utils import get_version
current_version = get_version()
```

## 🚫 **What NOT to Do**

### ❌ Don't Duplicate Versions
```python
# DON'T do this - creates version duplication
VERSION = "2.2.0"  # in some other file
__version__ = "2.2.0"  # in app/__init__.py
```

### ❌ Don't Hardcode Versions
```python
# DON'T do this - hardcoded version
print("Application version 2.2.0 starting...")

# DO this instead - use the centralized version
from app import __version__
print(f"Application version {__version__} starting...")
```

### ❌ Don't Put Versions in Configuration Files
```yaml
# DON'T do this in docker-compose.yml
version: '3.8'
services:
  app:
    image: myapp:2.2.0  # Hardcoded version

# DO this instead - use build-time substitution
# docker build -t myapp:$(python get_version.py) .
```

## 📋 **Version Update Checklist**

When updating the version, follow this checklist:

### 1. Code Changes
- [ ] Update `__version__` in `app/__init__.py`
- [ ] Test that `python get_version.py` returns the new version
- [ ] Verify application displays correct version in UI/logs

### 2. Documentation Updates
- [ ] Add new entry to `CHANGELOG.md`
- [ ] Update version badge in `README.md` (if needed)
- [ ] Update any version references in documentation

### 3. Git Operations
- [ ] Commit changes with clear message: `"Bump version to v2.2.1"`
- [ ] Create git tag: `git tag -a v$(python get_version.py) -m "Release v$(python get_version.py)"`
- [ ] Push changes and tags: `git push origin main --tags`

### 4. Build and Deploy
- [ ] Update Docker images: `docker build -t app:$(python get_version.py) .`
- [ ] Test deployment with new version
- [ ] Update production systems

## 🔍 **Troubleshooting**

### Version Mismatch Errors
If you see version mismatches:

1. **Check the source**: Verify `app/__init__.py` has the correct version
2. **Test the utility**: Run `python get_version.py` 
3. **Clear caches**: Restart Python processes that might have cached old versions
4. **Check imports**: Ensure code is importing from the right location

### get_version.py Errors
If `get_version.py` fails:

```bash
python get_version.py
# ERROR: Could not find __version__ in app/__init__.py
```

**Solution**: Check that `app/__init__.py` contains the line:
```python
__version__ = "X.X.X"
```

### Build Script Issues
If build scripts can't find version:

```bash
# Test the version access
python get_version.py

# Check path issues
ls -la app/__init__.py
ls -la get_version.py
```

## 🎯 **Best Practices**

### For Developers
1. **Always use the centralized version** - never hardcode versions
2. **Test version access** after making changes
3. **Use semantic versioning** for version numbers
4. **Update documentation** when changing versions

### For CI/CD Pipelines
```bash
# Good CI/CD practices
VERSION=$(python get_version.py)
echo "Building version $VERSION"

# Tag Docker images
docker build -t myapp:$VERSION .
docker build -t myapp:latest .

# Create GitHub releases
gh release create v$VERSION --title "Release v$VERSION"
```

### For Release Management
1. **Update version first** in `app/__init__.py`
2. **Test locally** with `python get_version.py`
3. **Update changelog** with new features
4. **Create Git tag** using the utility
5. **Deploy and verify** version in production

## 📚 **Related Files**

- `app/__init__.py` - Primary version source
- `get_version.py` - Version utility script  
- `app/core/utils.py` - Contains `get_version()` function
- `CHANGELOG.md` - Version history
- `docs/VERSIONING_STRATEGY.md` - Versioning strategy documentation

---

**Remember**: One version, one source, consistent everywhere! 🎯
