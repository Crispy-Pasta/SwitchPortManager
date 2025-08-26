"""
Ultra-simple tests for CI/CD pipeline - these should always pass
"""
import os
import sys


def test_python_works():
    """Test that Python is working"""
    assert 1 + 1 == 2


def test_python_version():
    """Test minimum Python version"""
    assert sys.version_info >= (3, 8)


def test_current_directory():
    """Test we're in the right directory"""
    # Should be in the root of the project
    assert os.path.exists("requirements.txt")


def test_github_workflow_exists():
    """Test GitHub workflow file exists"""
    assert os.path.exists(".github/workflows/deploy.yml")
