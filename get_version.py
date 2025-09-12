#!/usr/bin/env python3
"""
Simple utility to print the application version.
Used by shell scripts and other tools that need to get the version dynamically.
This script has NO fallback versions to ensure true centralization.
"""
import sys
import os
import re

# Directly read version from __init__.py file to avoid importing any modules
try:
    init_file_path = os.path.join(os.path.dirname(__file__), 'app', '__init__.py')
    with open(init_file_path, 'r') as f:
        content = f.read()
        # Extract version using regex
        version_match = re.search(r'__version__\s*=\s*["\']([^"\']*)["\']', content)
        if version_match:
            print(version_match.group(1))
            sys.exit(0)
        else:
            print("ERROR: Could not find __version__ in app/__init__.py", file=sys.stderr)
            sys.exit(1)
except FileNotFoundError:
    print("ERROR: Could not find app/__init__.py file", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"ERROR: Failed to read version from app/__init__.py: {e}", file=sys.stderr)
    sys.exit(1)
