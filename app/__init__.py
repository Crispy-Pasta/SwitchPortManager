#!/usr/bin/env python3
"""
Dell Switch Port Tracer - Modular Application Structure
======================================================

Improved application organization with blueprint-based architecture
for better maintainability and scalability.

Author: Network Operations Team
Version: 2.2.0 - Modular Refactor
"""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_httpauth import HTTPBasicAuth
import secrets
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()
auth = HTTPBasicAuth()

def create_app(config_name='default'):
    """Application factory pattern for better testing and deployment."""
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = secrets.token_hex(16)
    
    # Database configuration - PostgreSQL by default
    postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
    postgres_port = os.getenv('POSTGRES_PORT', '5432')
    postgres_db = os.getenv('POSTGRES_DB', 'dell_port_tracer')
    postgres_user = os.getenv('POSTGRES_USER', 'dell_tracer_user')
    postgres_password = os.getenv('POSTGRES_PASSWORD', 'dell_tracer_pass')
    
    # Construct PostgreSQL connection URL
    default_db_url = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'
    
    app.config.update({
        'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL', default_db_url),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'pool_recycle': 300,
            'pool_pre_ping': True
        }
    })
    
    # Initialize extensions with app
    db.init_app(app)
    
    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.api import api_bp
    from .routes.vlan import vlan_bp
    from .routes.management import mgmt_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(vlan_bp, url_prefix='/vlan')
    app.register_blueprint(mgmt_bp, url_prefix='/manage')
    
    return app
