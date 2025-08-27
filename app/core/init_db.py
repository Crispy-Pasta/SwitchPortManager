#!/usr/bin/env python3
"""
Database Initialization Script for Dell Switch Port Tracer
==========================================================

This script initializes the database schema for the Dell Switch Port Tracer
application. It's designed to be run during container startup to ensure
the database is properly configured before the application starts.

Features:
- Automatic database schema creation using SQLAlchemy models
- Connection retry logic for containerized deployments
- Comprehensive error handling and logging
- Support for both local and containerized PostgreSQL instances
- Idempotent operation (safe to run multiple times)

Usage:
- Standalone: python init_db.py
- Docker: Called automatically during container startup
- Manual: python init_db.py --force (recreates all tables)

Environment Variables Required:
- DATABASE_URL: Full PostgreSQL connection string
- POSTGRES_HOST: Database server hostname (fallback)
- POSTGRES_USER: Database username (fallback)
- POSTGRES_PASSWORD: Database password (fallback)
- POSTGRES_DB: Database name (fallback)

Security Notes:
- Never run with --force in production
- Ensure proper database backups before schema changes
- Monitor logs for connection issues or schema conflicts

Author: Network Operations Team
Version: 2.1.3
"""

import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('init_db.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

def wait_for_database(max_retries=30, retry_delay=2):
    """
    Wait for database to become available with exponential backoff.
    
    This function is crucial for containerized deployments where the
    application container may start before the database container is
    fully ready to accept connections.
    
    Args:
        max_retries (int): Maximum number of connection attempts
        retry_delay (int): Initial delay between retries (seconds)
    
    Returns:
        bool: True if database is available, False if max retries exceeded
    """
    from sqlalchemy import create_engine
    from sqlalchemy.exc import OperationalError
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        # Construct from individual components if DATABASE_URL not set
        postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
        postgres_port = os.getenv('POSTGRES_PORT', '5432')
        postgres_db = os.getenv('POSTGRES_DB', 'port_tracer_db')
        postgres_user = os.getenv('POSTGRES_USER', 'dell_tracer_user')
        postgres_password = os.getenv('POSTGRES_PASSWORD', 'secure_password123')
        database_url = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'
    
    logger.info(f"Waiting for database at {database_url.split('@')[1] if '@' in database_url else 'unknown host'}...")
    
    for attempt in range(1, max_retries + 1):
        try:
            # Attempt to create engine and connect
            engine = create_engine(database_url)
            connection = engine.connect()
            connection.close()
            engine.dispose()
            
            logger.info(f"✅ Database connection successful after {attempt} attempt(s)")
            return True
            
        except OperationalError as e:
            if attempt == max_retries:
                logger.error(f"❌ Failed to connect to database after {max_retries} attempts")
                logger.error(f"Last error: {str(e)}")
                return False
            
            wait_time = min(retry_delay * (2 ** (attempt - 1)), 30)  # Exponential backoff, max 30s
            logger.warning(f"Database not ready (attempt {attempt}/{max_retries}). Retrying in {wait_time}s...")
            time.sleep(wait_time)
            
        except Exception as e:
            logger.error(f"❌ Unexpected database connection error: {str(e)}")
            return False
    
    return False

def initialize_database(force_recreate=False):
    """
    Initialize the database schema using SQLAlchemy models.
    
    This function creates all required tables, indexes, and constraints
    based on the SQLAlchemy model definitions. It's designed to be
    idempotent and safe to run multiple times.
    
    Args:
        force_recreate (bool): If True, drops and recreates all tables
                              (DANGEROUS - only for development)
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    try:
        # Import Flask app and database models
        logger.info("🔧 Importing application modules...")
        from port_tracer_web import app
        from app.core.database import db, Site, Floor, Switch
        
        # Create application context for database operations
        with app.app_context():
            if force_recreate:
                logger.warning("⚠️  FORCE RECREATE MODE - Dropping all existing tables...")
                db.drop_all()
                logger.info("🗑️  All tables dropped successfully")
            
            # Create all tables based on SQLAlchemy models
            logger.info("🏗️  Creating database tables...")
            db.create_all()
            
            # Verify table creation
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            required_tables = ['site', 'floor', 'switch']
            created_tables = []
            
            for table in required_tables:
                if table in existing_tables:
                    created_tables.append(table)
                    logger.info(f"✅ Table '{table}' created/verified successfully")
                else:
                    logger.error(f"❌ Table '{table}' not found after creation")
                    return False
            
            # Check if tables have proper structure
            logger.info("🔍 Verifying table structures...")
            
            # Check Site table structure
            site_columns = [col['name'] for col in inspector.get_columns('site')]
            expected_site_columns = ['id', 'name']
            if all(col in site_columns for col in expected_site_columns):
                logger.info("✅ Site table structure verified")
            else:
                logger.error(f"❌ Site table missing columns. Expected: {expected_site_columns}, Found: {site_columns}")
            
            # Check Floor table structure
            floor_columns = [col['name'] for col in inspector.get_columns('floor')]
            expected_floor_columns = ['id', 'name', 'site_id']
            if all(col in floor_columns for col in expected_floor_columns):
                logger.info("✅ Floor table structure verified")
            else:
                logger.error(f"❌ Floor table missing columns. Expected: {expected_floor_columns}, Found: {floor_columns}")
            
            # Check Switch table structure
            switch_columns = [col['name'] for col in inspector.get_columns('switch')]
            expected_switch_columns = ['id', 'name', 'ip_address', 'model', 'description', 'enabled', 'floor_id']
            if all(col in switch_columns for col in expected_switch_columns):
                logger.info("✅ Switch table structure verified")
            else:
                logger.error(f"❌ Switch table missing columns. Expected: {expected_switch_columns}, Found: {switch_columns}")
            
            # Check for existing data
            site_count = db.session.query(Site).count()
            floor_count = db.session.query(Floor).count()
            switch_count = db.session.query(Switch).count()
            
            logger.info(f"📊 Database statistics:")
            logger.info(f"   • Sites: {site_count}")
            logger.info(f"   • Floors: {floor_count}")
            logger.info(f"   • Switches: {switch_count}")
            
            if site_count == 0:
                logger.warning("⚠️  Database is empty. Consider importing initial data.")
                logger.info("💡 You can import data using:")
                logger.info("   • Admin interface (web UI)")
                logger.info("   • API endpoints")
                logger.info("   • SQL import scripts")
            
            logger.info("🎉 Database initialization completed successfully!")
            return True
            
    except ImportError as e:
        logger.error(f"❌ Failed to import application modules: {str(e)}")
        logger.error("💡 Ensure all required Python packages are installed")
        return False
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {str(e)}")
        logger.error("💡 Check database permissions and connection settings")
        return False

def check_environment_variables():
    """
    Verify that required environment variables are set.
    
    Returns:
        bool: True if all required variables are present, False otherwise
    """
    logger.info("🔍 Checking environment variables...")
    
    required_vars = [
        'POSTGRES_DB',
        'POSTGRES_USER', 
        'POSTGRES_PASSWORD'
    ]
    
    optional_vars = [
        'DATABASE_URL',
        'POSTGRES_HOST',
        'POSTGRES_PORT',
        'SWITCH_USERNAME',
        'SWITCH_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("💡 Please check your .env file or environment configuration")
        return False
    
    logger.info("✅ Required environment variables are present")
    
    # Log optional variable status
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive information
            if 'PASSWORD' in var or 'SECRET' in var:
                masked_value = '*' * len(value) if len(value) > 0 else 'NOT_SET'
                logger.info(f"   • {var}: {masked_value}")
            else:
                logger.info(f"   • {var}: {value}")
        else:
            logger.info(f"   • {var}: NOT_SET (using default)")
    
    return True

def main():
    """
    Main initialization function with comprehensive error handling.
    """
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("🚀 Dell Switch Port Tracer - Database Initialization")
    logger.info("=" * 60)
    logger.info(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Parse command line arguments
    force_recreate = '--force' in sys.argv
    
    if force_recreate:
        logger.warning("⚠️  FORCE MODE ENABLED - This will recreate all tables!")
        logger.warning("⚠️  Make sure you have backups before proceeding!")
    
    try:
        # Step 1: Check environment variables
        if not check_environment_variables():
            logger.error("❌ Environment validation failed")
            sys.exit(1)
        
        # Step 2: Wait for database to become available
        if not wait_for_database():
            logger.error("❌ Database connection timeout")
            sys.exit(1)
        
        # Step 3: Initialize database schema
        if not initialize_database(force_recreate=force_recreate):
            logger.error("❌ Database initialization failed")
            sys.exit(1)
        
        # Success!
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 60)
        logger.info("🎉 Database initialization completed successfully!")
        logger.info(f"Total time: {duration:.2f} seconds")
        logger.info("=" * 60)
        
        # Provide next steps
        logger.info("📋 Next steps:")
        logger.info("   1. Start the Dell Port Tracer application")
        logger.info("   2. Import initial data (sites, floors, switches)")
        logger.info("   3. Configure switch SSH credentials")
        logger.info("   4. Test connectivity and functionality")
        
        sys.exit(0)
        
    except KeyboardInterrupt:
        logger.warning("⚠️  Initialization interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"❌ Unexpected error during initialization: {str(e)}")
        logger.error("💡 Check the logs above for detailed error information")
        sys.exit(1)

if __name__ == "__main__":
    main()
