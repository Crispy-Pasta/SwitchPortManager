#!/usr/bin/env python3
"""
WSGI Entry Point for Dell Switch Port Tracer
===========================================

This module serves as the WSGI application entry point for production
deployment using Gunicorn or other WSGI servers.

Usage with Gunicorn:
    gunicorn --workers 4 --bind 0.0.0.0:5000 wsgi:application

Features:
- Production-ready Flask application factory pattern
- Environment variable configuration
- Proper error handling and logging
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path for imports
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import the Flask application factory
from app.main import create_app

# Create the WSGI application instance
application = create_app()

# For compatibility with various WSGI servers
app = application

if __name__ == "__main__":
    # This allows running with `python wsgi.py` for testing
    print("🚀 Starting Dell Switch Port Tracer via WSGI...")
    print("⚠️  Note: For production, use a WSGI server like Gunicorn")
    
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    application.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )
