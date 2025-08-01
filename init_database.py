#!/usr/bin/env python3
"""
Database Initialization Script for Dell Port Tracer
====================================================

This script initializes the database with the required tables and sample data.
It supports both PostgreSQL (production) and SQLite (development).
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from database import db, Site, Floor, Switch

def create_app():
    """Create Flask application with database configuration."""
    app = Flask(__name__)
    
    # Database configuration - PostgreSQL by default, fallback to SQLite for testing
    postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
    postgres_port = os.getenv('POSTGRES_PORT', '5432')
    postgres_db = os.getenv('POSTGRES_DB', 'dell_port_tracer')
    postgres_user = os.getenv('POSTGRES_USER', 'dell_tracer_user')
    postgres_password = os.getenv('POSTGRES_PASSWORD', 'dell_tracer_pass')
    
    # Try PostgreSQL first
    postgres_url = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'
    
    # Check if we should use SQLite for testing
    use_sqlite = os.getenv('USE_SQLITE_FOR_TESTING', 'false').lower() == 'true'
    
    if use_sqlite:
        print("🔧 Using SQLite for testing...")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///switches.db'
    else:
        print(f"🐘 Attempting to connect to PostgreSQL: {postgres_host}:{postgres_port}")
        app.config['SQLALCHEMY_DATABASE_URI'] = postgres_url
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,
        'pool_pre_ping': True
    }
    
    db.init_app(app)
    return app

def test_database_connection(app):
    """Test database connection."""
    try:
        with app.app_context():
            # Try to connect to the database
            db.engine.connect()
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def initialize_database(app):
    """Initialize database with tables and sample data."""
    try:
        with app.app_context():
            print("🔨 Creating database tables...")
            db.create_all()
            
            # Check if we already have data
            if Site.query.first():
                print("📊 Database already has data. Skipping initialization.")
                return True
            
            print("📝 Creating sample data...")
            
            # Create sample sites
            site1 = Site(name="HQ")
            site2 = Site(name="Branch-A")
            site3 = Site(name="Branch-B")
            
            db.session.add_all([site1, site2, site3])
            db.session.flush()  # Get IDs without committing
            
            # Create sample floors
            hq_floor1 = Floor(name="Floor 1", site_id=site1.id)
            hq_floor2 = Floor(name="Floor 2", site_id=site1.id)
            branch_a_floor1 = Floor(name="Floor 1", site_id=site2.id)
            branch_b_floor1 = Floor(name="Floor 1", site_id=site3.id)
            
            db.session.add_all([hq_floor1, hq_floor2, branch_a_floor1, branch_b_floor1])
            db.session.flush()  # Get IDs without committing
            
            # Create sample switches
            switches = [
                Switch(name="SW-HQ-F1-01", ip_address="10.1.1.10", model="Dell N3248", 
                      description="HQ Floor 1 Main Switch", enabled=True, floor_id=hq_floor1.id),
                Switch(name="SW-HQ-F1-02", ip_address="10.1.1.11", model="Dell N3024P", 
                      description="HQ Floor 1 PoE Switch", enabled=True, floor_id=hq_floor1.id),
                Switch(name="SW-HQ-F2-01", ip_address="10.1.2.10", model="Dell N3248", 
                      description="HQ Floor 2 Main Switch", enabled=True, floor_id=hq_floor2.id),
                Switch(name="SW-BA-F1-01", ip_address="10.2.1.10", model="Dell N2048", 
                      description="Branch A Floor 1 Switch", enabled=True, floor_id=branch_a_floor1.id),
                Switch(name="SW-BB-F1-01", ip_address="10.3.1.10", model="Dell N3024P", 
                      description="Branch B Floor 1 Switch", enabled=True, floor_id=branch_b_floor1.id),
            ]
            
            db.session.add_all(switches)
            db.session.commit()
            
            print("✅ Database initialized successfully!")
            print(f"   Sites: {Site.query.count()}")
            print(f"   Floors: {Floor.query.count()}")
            print(f"   Switches: {Switch.query.count()}")
            
            return True
            
    except Exception as e:
        print(f"❌ Database initialization failed: {str(e)}")
        db.session.rollback()
        return False

def main():
    """Main function."""
    print("🚀 Dell Port Tracer Database Initialization")
    print("=" * 50)
    
    # Create Flask app
    app = create_app()
    
    # Test database connection
    if not test_database_connection(app):
        print("\n💡 Suggestion: If PostgreSQL is not available, you can use SQLite for testing:")
        print("   set USE_SQLITE_FOR_TESTING=true")
        print("   python init_database.py")
        return False
    
    # Initialize database
    if initialize_database(app):
        print("\n🎉 Database setup completed successfully!")
        print("\nYou can now run the application:")
        print("   python port_tracer_web.py")
        return True
    else:
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
