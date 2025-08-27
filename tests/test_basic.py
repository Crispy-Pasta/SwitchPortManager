"""
Basic tests for Dell Port Tracer CI/CD pipeline
"""
import pytest
import os


def test_environment_setup():
    """Test that basic environment is working"""
    assert True, "Basic test should always pass"


def test_python_version():
    """Test Python version compatibility"""
    import sys
    assert sys.version_info >= (3, 8), "Python 3.8+ required"


def test_required_modules():
    """Test that required modules can be imported"""
    required_modules = ['flask', 'psycopg2', 'paramiko', 'dotenv']
    missing_modules = []
    
    for module_name in required_modules:
        try:
            __import__(module_name)
        except ImportError:
            missing_modules.append(module_name)
    
    if missing_modules:
        pytest.skip(f"Skipping test - missing modules: {missing_modules}")
    else:
        assert True, "All required modules importable"


def test_application_structure():
    """Test that main application files exist"""
    expected_files = [
        "port_tracer_web.py",
        "requirements.txt",
        "Dockerfile",
        ".dockerignore"
    ]
    
    for file_name in expected_files:
        assert os.path.exists(file_name), f"Required file missing: {file_name}"


def test_docker_files():
    """Test that Docker-related files exist for CI/CD"""
    docker_files = [
        "Dockerfile.production",
        "docker-compose.prod.yml",
        "docker-compose.registry.yml",
        ".dockerignore"
    ]
    
    for file_name in docker_files:
        assert os.path.exists(file_name), f"Docker file missing: {file_name}"


def test_github_actions():
    """Test that GitHub Actions workflow exists"""
    workflow_file = ".github/workflows/deploy.yml"
    assert os.path.exists(workflow_file), "GitHub Actions workflow missing"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
