#!/usr/bin/env python3
"""
Dell Switch Port Tracer - Database Migration Script
==================================================

This script ensures the PostgreSQL database schema is properly set up
and migrates data from any existing configuration files.

Features:
- Creates database tables if they don't exist
- Migrates data from legacy JSON configuration files
- Validates database connectivity and permissions
- Provides rollback capabilities
- Safe to run multiple times (idempotent)

Usage:
    python migrate_database.py [--create-sample-data]
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from database import db, Site, Floor, Switch

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_database_url():
    """Construct PostgreSQL connection URL from environment variables."""
    postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
    postgres_port = os.getenv('POSTGRES_PORT', '5432')
    postgres_db = os.getenv('POSTGRES_DB', 'dell_port_tracer')
    postgres_user = os.getenv('POSTGRES_USER', 'dell_tracer_user')
    postgres_password = os.getenv('POSTGRES_PASSWORD', 'dell_tracer_pass')
    
    default_db_url = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'
    return os.getenv('DATABASE_URL', default_db_url)

def test_database_connection():
    """Test database connectivity and permissions."""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            logger.info(f"✅ Database connection successful")
            logger.info(f"📊 PostgreSQL version: {version}")
            
        # Test table creation permissions
        with engine.connect() as connection:
            connection.execute(text("CREATE TABLE IF NOT EXISTS migration_test (id SERIAL PRIMARY KEY);"))
            connection.execute(text("DROP TABLE IF EXISTS migration_test;"))
            connection.commit()
            logger.info("✅ Database permissions validated")
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False

def create_tables(app):
    """Create database tables using SQLAlchemy models."""
    try:
        with app.app_context():
            logger.info("🔨 Creating database tables...")
            db.create_all()
            logger.info("✅ Database tables created successfully")
            return True
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {str(e)}")
        return False

def migrate_from_json_config():
    """Migrate data from legacy JSON configuration files."""
    config_files = [
        'switches.json',
        'config/switches.json', 
        'data/switches.json'
    ]
    
    migrated_data = False
    
    for config_file in config_files:
        if os.path.exists(config_file):
            logger.info(f"📥 Found legacy configuration file: {config_file}")
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Extract sites data structure
                sites_data = config_data.get('sites', {})
                
                if not sites_data:
                    logger.warning(f"⚠️  No sites data found in {config_file}")
                    continue
                
                # Migrate each site
                for site_name, floors_data in sites_data.items():
                    logger.info(f"🏢 Migrating site: {site_name}")
                    
                    # Create or get site
                    site = Site.query.filter_by(name=site_name).first()
                    if not site:
                        site = Site(name=site_name)
                        db.session.add(site)
                        db.session.flush()  # Get ID without committing
                        logger.info(f"   ✅ Created site: {site_name}")
                    else:
                        logger.info(f"   ℹ️  Site already exists: {site_name}")
                    
                    # Migrate floors and switches
                    for floor_name, switches_list in floors_data.items():
                        logger.info(f"🏢 Migrating floor: {floor_name}")
                        
                        # Create or get floor
                        floor = Floor.query.filter_by(name=floor_name, site_id=site.id).first()
                        if not floor:
                            floor = Floor(name=floor_name, site_id=site.id)
                            db.session.add(floor)
                            db.session.flush()  # Get ID without committing
                            logger.info(f"     ✅ Created floor: {floor_name}")
                        else:
                            logger.info(f"     ℹ️  Floor already exists: {floor_name}")
                        
                        # Migrate switches
                        for switch_data in switches_list:
                            switch_name = switch_data.get('name')
                            switch_ip = switch_data.get('ip')
                            
                            if not switch_name or not switch_ip:
                                logger.warning(f"     ⚠️  Invalid switch data: {switch_data}")
                                continue
                            
                            # Create or get switch
                            switch = Switch.query.filter_by(name=switch_name).first()
                            if not switch:
                                switch = Switch(
                                    name=switch_name,
                                    ip_address=switch_ip,
                                    model=switch_data.get('model', 'Dell N3248'),
                                    description=switch_data.get('description', ''),
                                    enabled=switch_data.get('enabled', True),
                                    floor_id=floor.id
                                )
                                db.session.add(switch)
                                logger.info(f"       ✅ Migrated switch: {switch_name} ({switch_ip})")
                            else:
                                logger.info(f"       ℹ️  Switch already exists: {switch_name}")
                
                # Commit all changes for this config file
                db.session.commit()
                logger.info(f"✅ Successfully migrated data from {config_file}")
                migrated_data = True
                
                # Create backup of original file
                backup_file = f"{config_file}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                os.rename(config_file, backup_file)
                logger.info(f"📦 Original file backed up as: {backup_file}")
                
            except Exception as e:
                logger.error(f"❌ Failed to migrate {config_file}: {str(e)}")
                db.session.rollback()
    
    if not migrated_data:
        logger.info("ℹ️  No legacy configuration files found to migrate")
    
    return migrated_data

def create_sample_data():
    """Create sample data for testing and demonstration."""
    logger.info("🌟 Creating sample data...")
    
    try:
        # Create sample site
        sample_site = Site.query.filter_by(name='SAMPLE_SITE').first()
        if not sample_site:
            sample_site = Site(name='SAMPLE_SITE')
            db.session.add(sample_site)
            db.session.flush()
        
        # Create sample floors
        for floor_num in ['11', '12', 'GF']:
            sample_floor = Floor.query.filter_by(name=floor_num, site_id=sample_site.id).first()
            if not sample_floor:
                sample_floor = Floor(name=floor_num, site_id=sample_site.id)
                db.session.add(sample_floor)
                db.session.flush()
                
                # Create sample switches for each floor
                for switch_num in range(1, 3):
                    switch_name = f"SAMPLE-F{floor_num}-R{switch_num}-VAS-01"
                    switch_ip = f"10.50.{floor_num if floor_num != 'GF' else '0'}.{10 + switch_num}"
                    
                    sample_switch = Switch(
                        name=switch_name,
                        ip_address=switch_ip,
                        model='Dell N3248',
                        description=f'Sample switch for floor {floor_num}',
                        enabled=True,
                        floor_id=sample_floor.id
                    )
                    db.session.add(sample_switch)
        
        db.session.commit()
        logger.info("✅ Sample data created successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create sample data: {str(e)}")
        db.session.rollback()
        return False

def validate_migration():
    """Validate that migration was successful."""
    logger.info("🔍 Validating migration...")
    
    try:
        site_count = Site.query.count()
        floor_count = Floor.query.count()
        switch_count = Switch.query.count()
        
        logger.info(f"📊 Migration validation results:")
        logger.info(f"   Sites: {site_count}")
        logger.info(f"   Floors: {floor_count}")
        logger.info(f"   Switches: {switch_count}")
        
        if site_count > 0 and floor_count > 0:
            logger.info("✅ Migration validation passed")
            return True
        else:
            logger.warning("⚠️  Migration validation failed - no data found")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration validation error: {str(e)}")
        return False

def main():
    """Main migration function."""
    parser = argparse.ArgumentParser(description='Dell Port Tracer Database Migration')
    parser.add_argument('--create-sample-data', action='store_true', 
                       help='Create sample data for testing')
    parser.add_argument('--skip-connection-test', action='store_true',
                       help='Skip database connection test')
    args = parser.parse_args()
    
    logger.info("🚀 Starting Dell Port Tracer database migration...")
    
    # Test database connection
    if not args.skip_connection_test:
        if not test_database_connection():
            logger.error("❌ Migration aborted due to connection failure")
            sys.exit(1)
    
    # Initialize Flask app for database context
    from flask import Flask
    app = Flask(__name__)
    
    # Configure database
    database_url = get_database_url()
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 300,
        'pool_pre_ping': True
    }
    
    # Initialize database with app
    db.init_app(app)
    
    # Create tables
    if not create_tables(app):
        logger.error("❌ Migration aborted due to table creation failure")
        sys.exit(1)
    
    # Migrate legacy data
    with app.app_context():
        migrate_from_json_config()
        
        # Create sample data if requested
        if args.create_sample_data:
            create_sample_data()
        
        # Validate migration
        if not validate_migration():
            logger.warning("⚠️  Migration completed with warnings")
        else:
            logger.info("🎉 Migration completed successfully!")

if __name__ == '__main__':
    main()
