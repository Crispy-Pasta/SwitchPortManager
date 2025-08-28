#!/usr/bin/env python3
"""
Root-level Database Initialization Wrapper
==========================================

This wrapper script calls the actual database initialization script
located in app/core/init_db.py. This maintains Docker compatibility
while keeping the actual initialization logic organized in the app structure.
"""

import sys
import os
from pathlib import Path

# Add the app directory to Python path for imports
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

# Import and run the actual initialization script
if __name__ == "__main__":
    from app.core.init_db import main
    main()
