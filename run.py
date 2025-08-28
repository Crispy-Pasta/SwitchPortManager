#!/usr/bin/env python3
"""
Dell Switch Port Tracer - Application Entry Point

This script serves as the main entry point for running the Dell Switch Port Tracer
application. It can be used for both development and production environments.
"""

import os
import sys
from pathlib import Path

# Add the app directory to Python path for imports
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

from app.main import create_app

def main():
    """Main application entry point"""
    # Load environment from .env file if it exists
    from dotenv import load_dotenv
    load_dotenv()
    
    # Create Flask application
    app = create_app()
    
    # Get configuration from environment
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    
print(f"🚀 Starting Dell Switch Port Tracer v2.2.0")
    print(f"   Host: {host}:{port}")
    print(f"   Debug: {debug}")
    print(f"   Environment: {os.getenv('FLASK_ENV', 'production')}")
    
    # Run the application
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True
    )

if __name__ == '__main__':
    main()
