#!/usr/bin/env python3
"""
Dell Switch Port Tracer & VLAN Manager - Enterprise Edition
===========================================================

A comprehensive network management solution for Dell switches featuring
MAC address tracing and advanced VLAN management capabilities.

🏢 ENTERPRISE FEATURES:
- Multi-site, multi-floor switch management (27+ sites, 155+ switches)
- Advanced VLAN Manager with port assignment and safety checks
- Windows AD integration with role-based permissions (OSS/NetAdmin/SuperAdmin)
- Dell N2000/N3000/N3200 series switch support (N2048, N3024P, N3248 models)
- Real-time MAC address tracing with port configuration details
- Comprehensive audit logging and monitoring
- Modern, responsive web interface with KMC branding
- Consistent UI/UX design with standardized modal dialogs and button sizing
- Enhanced inventory layout: 1800px main content with 500px sidebar for optimal screen utilization

🔧 VLAN MANAGEMENT CAPABILITIES:
- Port VLAN assignment with safety validation
- Uplink port protection and detection
- VLAN creation and naming standardization
- Port description management
- Preview and confirmation workflows
- Switch model-aware interface naming

⚡ PERFORMANCE & SCALABILITY:
- Concurrent switch processing (8 workers max per site)
- Per-site user limits (10 concurrent users max)
- 6x faster MAC tracing (30s → 5s for 10 switches)
- Thread-safe operations with proper locking
- 60-second timeout protection

🐳 DEPLOYMENT READY:
- Docker and Kubernetes deployment ready
- Production-grade security and health checks
- Auto-deployment with 1-minute intervals
- Environment-based configuration

📊 MONITORING & TROUBLESHOOTING:
- Real-time performance metrics
- CPU safety monitoring
- Switch protection status monitoring
- Detailed audit trails with timing
- Enhanced error handling and logging
- Progress tracking for large batches

Repository: https://github.com/Crispy-Pasta/DellPortTracer
Version: 2.1.3
Author: Network Operations Team
Last Updated: August 2025 - Enhanced VLAN Management with Interface Range Optimization
License: MIT

🔧 TROUBLESHOOTING:
- Check logs: port_tracer.log (system) | audit.log (user actions)
- Monitor concurrent users per site in CONCURRENT_USERS_PER_SITE
- Verify Dell switch SSH limits (max 10 concurrent sessions)
- Review environment variables for performance tuning
- VLAN operations require NetAdmin or SuperAdmin privileges
"""

import paramiko
import logging
import logging.handlers
import time
import psutil
import json
import os
from datetime import datetime, timezone
from flask import Flask, render_template, render_template_string, request, jsonify, session, redirect, url_for
from flask_httpauth import HTTPBasicAuth
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import secrets
import threading
import concurrent.futures
from collections import defaultdict
import re

# Import refactored modules
from app.auth.auth import verify_user, get_user_permissions, WINDOWS_AUTH_AVAILABLE
from app.core.switch_manager import (
    DellSwitchSSH, detect_switch_model_from_config, is_uplink_port, 
    get_port_caution_info, parse_mac_table_output, trace_single_switch
)
from app.core.utils import (
    is_valid_mac, get_mac_format_error_message, format_switches_for_frontend,
    get_site_floor_switches, apply_role_based_filtering, load_switches_from_database
)
from app.api.routes import api_bp

# Load CPU Safety Monitor
from app.monitoring.cpu_monitor import initialize_cpu_monitor, get_cpu_monitor

# Load Switch Protection Monitor
try:
    from app.monitoring.switch_monitor import initialize_switch_protection_monitor, get_switch_protection_monitor
    SWITCH_PROTECTION_AVAILABLE = True
except ImportError:
    SWITCH_PROTECTION_AVAILABLE = False

# Load environment variables first
load_dotenv()

# Flask app (fix template and static folder paths)
import os
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static'))

# Session timeout configuration
from datetime import timedelta

# Read session timeout from environment (default 5 minutes)
session_timeout = int(os.getenv('PERMANENT_SESSION_LIFETIME', '5'))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=session_timeout)

# Session security settings (read from environment variables)
app.config['SESSION_COOKIE_SECURE'] = os.getenv('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = os.getenv('SESSION_COOKIE_HTTPONLY', 'true').lower() == 'true'
app.config['SESSION_COOKIE_SAMESITE'] = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
app.secret_key = secrets.token_hex(16)
auth = HTTPBasicAuth()

# Database configuration - PostgreSQL by default
postgres_host = os.getenv('POSTGRES_HOST', 'localhost')
postgres_port = os.getenv('POSTGRES_PORT', '5432')
postgres_db = os.getenv('POSTGRES_DB', 'dell_port_tracer')
postgres_user = os.getenv('POSTGRES_USER', 'dell_tracer_user')
postgres_password = os.getenv('POSTGRES_PASSWORD', 'dell_tracer_pass')

# Construct PostgreSQL connection URL
default_db_url = f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}'

# Allow override via DATABASE_URL environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', default_db_url)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,  # Recycle connections every 5 minutes
    'pool_pre_ping': True  # Verify connections before use
}

# Initialize database
from app.core.database import db, Site, Floor, Switch
db.init_app(app)

# Configuration
SWITCH_USERNAME = os.getenv('SWITCH_USERNAME')
SWITCH_PASSWORD = os.getenv('SWITCH_PASSWORD')

# User roles and credentials
USERS = {
    'oss': {'password': os.getenv('OSS_PASSWORD', 'oss123'), 'role': 'oss'},
    'netadmin': {'password': os.getenv('NETADMIN_PASSWORD', 'netadmin123'), 'role': 'netadmin'},
    'superadmin': {'password': os.getenv('SUPERADMIN_PASSWORD', 'superadmin123'), 'role': 'superadmin'},
    # Legacy admin user (maps to superadmin)
    'admin': {'password': os.getenv('WEB_PASSWORD', 'password'), 'role': 'superadmin'}
}

# Role permissions
ROLE_PERMISSIONS = {
    'oss': {
        'show_vlan_details': False,  # Only for access ports
        'show_uplink_ports': False,  # Hide uplink ports
        'show_trunk_general_vlans': False,  # Hide VLAN details for trunk/general
        'show_switch_names': False  # Hide switch names for security
    },
    'netadmin': {
        'show_vlan_details': True,
        'show_uplink_ports': True,
        'show_trunk_general_vlans': True,
        'show_switch_names': True  # Show actual switch names
    },
    'superadmin': {
        'show_vlan_details': True,
        'show_uplink_ports': True,
        'show_trunk_general_vlans': True,
        'show_switch_names': True  # Show actual switch names
    }
}

# Configure logging with optional syslog support
handlers = [
    logging.FileHandler('port_tracer.log'),
    logging.StreamHandler()
]

# Add syslog handler if configured and available (SolarWinds SEM compatible)
syslog_server = os.getenv('SYSLOG_SERVER')
syslog_enabled = os.getenv('SYSLOG_ENABLED', 'false').lower() == 'true'
if syslog_enabled and syslog_server and syslog_server.lower() not in ['', 'none', 'disabled']:
    try:
        syslog_port = int(os.getenv('SYSLOG_PORT', 514))
        # Use facility LOCAL0 (16) for custom applications - SolarWinds SEM friendly
        syslog_handler = logging.handlers.SysLogHandler(
            address=(syslog_server, syslog_port),
            facility=logging.handlers.SysLogHandler.LOG_LOCAL0
        )
        # RFC3164 compliant format for better SolarWinds SEM parsing
        syslog_formatter = logging.Formatter(
            'Dell-Port-Tracer[%(process)d]: %(levelname)s - %(funcName)s - %(message)s'
        )
        syslog_handler.setFormatter(syslog_formatter)
        handlers.append(syslog_handler)
        print(f"✅ Syslog logging enabled for SolarWinds SEM: {syslog_server}:{syslog_port} (LOCAL0 facility)")
        
        # Send initial test message to confirm syslog connectivity
        test_logger = logging.getLogger('syslog_test')
        test_logger.addHandler(syslog_handler)
        test_logger.setLevel(logging.INFO)
        test_logger.info("Dell Port Tracer application started - Syslog connectivity test")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not connect to syslog server {syslog_server}: {str(e)}")
        print("   Continuing without syslog logging...")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)

# Log credential loading status for monitoring (after logger is initialized)
logger.info(f"Switch credentials loaded - Username: {'SET' if SWITCH_USERNAME else 'NOT_SET'}, Password: {'SET' if SWITCH_PASSWORD else 'NOT_SET'}")

# CPU Safety configuration (override concurrent limits based on CPU protection zones)
cpu_monitor = initialize_cpu_monitor(
    green_threshold=float(os.getenv('CPU_GREEN_THRESHOLD', '40')),
    yellow_threshold=float(os.getenv('CPU_YELLOW_THRESHOLD', '60')),
    red_threshold=float(os.getenv('CPU_RED_THRESHOLD', '80'))
)

# Switch Protection Monitor initialization
switch_monitor = None
if SWITCH_PROTECTION_AVAILABLE:
    switch_monitor = initialize_switch_protection_monitor(
        max_connections_per_switch=int(os.getenv('MAX_CONNECTIONS_PER_SWITCH', '8')),
        max_total_connections=int(os.getenv('MAX_TOTAL_CONNECTIONS', '64')),
        commands_per_second_limit=int(os.getenv('COMMANDS_PER_SECOND_LIMIT', '10'))
    )
    logger.info("Switch protection monitor initialized")
else:
    logger.warning("Switch protection monitor not available - switches may be vulnerable to overload")

# Concurrent user tracking per site (Dell switch limit: 10 concurrent SSH sessions)
CONCURRENT_USERS_PER_SITE = defaultdict(lambda: {'count': 0, 'lock': threading.Lock()})
MAX_CONCURRENT_USERS_PER_SITE = int(os.getenv('MAX_CONCURRENT_USERS_PER_SITE', '10'))
MAX_WORKERS_PER_SITE = int(os.getenv('MAX_WORKERS_PER_SITE', '8'))  # Parallel switch connections

# Audit logging for user actions (with optional syslog support)
audit_logger = logging.getLogger('audit')
audit_handler = logging.FileHandler('audit.log')
audit_formatter = logging.Formatter('%(asctime)s - AUDIT - %(message)s')
audit_handler.setFormatter(audit_formatter)
audit_logger.addHandler(audit_handler)

# Add syslog handler for audit logs if syslog is enabled
if syslog_enabled and syslog_server and syslog_server.lower() not in ['', 'none', 'disabled']:
    try:
        audit_syslog_handler = logging.handlers.SysLogHandler(
            address=(syslog_server, syslog_port),
            facility=logging.handlers.SysLogHandler.LOG_LOCAL1  # Use LOCAL1 for audit logs
        )
        audit_syslog_formatter = logging.Formatter(
            'Dell-Port-Tracer-AUDIT[%(process)d]: %(levelname)s - %(message)s'
        )
        audit_syslog_handler.setFormatter(audit_syslog_formatter)
        audit_logger.addHandler(audit_syslog_handler)
        print(f"✅ Audit syslog logging enabled: {syslog_server}:{syslog_port} (LOCAL1 facility)")
    except Exception as e:
        print(f"⚠️  Warning: Could not configure audit syslog: {str(e)}")

audit_logger.setLevel(logging.INFO)

# Load switches configuration
def load_switches():
    """Load switches from PostgreSQL."""
    try:
        sites_with_switches = {}
        sites = Site.query.all()
        for site in sites:
            floors = Floor.query.filter_by(site_id=site.id).all()
            floors_with_switches = {}
            for floor in floors:
                switches = Switch.query.filter_by(floor_id=floor.id, enabled=True).all()
                switch_data = [{'name': sw.name, 'ip': sw.ip_address} for sw in switches]
                if switch_data:
                    floors_with_switches[floor.name] = switch_data
            if floors_with_switches:
                sites_with_switches[site.name] = floors_with_switches
        if not sites_with_switches:
            return {"sites": []}
        else:
            return {"sites": sites_with_switches}
    except Exception as e:
        logger.error(f"Failed to load switches from the database: {str(e)}")
        return {"sites": []}

# Authentication functions moved to auth.py module

# Switch management functions moved to switch_manager.py module
# DellSwitchSSH class moved to switch_manager.py module

# parse_mac_table_output function moved to switch_manager.py module

# Utility functions moved to utils.py module

# trace_single_switch function moved to switch_manager.py module

def check_concurrent_user_limit(site):
    """Check if the concurrent user limit for a site has been reached."""
    site_tracker = CONCURRENT_USERS_PER_SITE[site]
    
    with site_tracker['lock']:
        if site_tracker['count'] >= MAX_CONCURRENT_USERS_PER_SITE:
            return False
        site_tracker['count'] += 1
        return True

def release_concurrent_user_slot(site):
    """Release a concurrent user slot for a site."""
    site_tracker = CONCURRENT_USERS_PER_SITE[site]
    
    with site_tracker['lock']:
        if site_tracker['count'] > 0:
            site_tracker['count'] -= 1

def trace_mac_on_switches(switches, mac_address, username):
    """Trace MAC address across specified switches using concurrent processing."""
    start_time = time.time()
    site = switches[0]['site'] if switches else 'unknown'
    
    # Check concurrent user limit per site (Dell switch SSH session limit)
    if not check_concurrent_user_limit(site):
        audit_logger.warning(f"User: {username} - TRACE REJECTED - Site: {site} - Concurrent user limit ({MAX_CONCURRENT_USERS_PER_SITE}) reached")
        return [{
            'switch_name': 'System',
            'switch_ip': 'N/A',
            'status': 'error',
            'message': f'Too many concurrent users for site {site}. Maximum {MAX_CONCURRENT_USERS_PER_SITE} users allowed. Please try again in a moment.'
        }]
    
    try:
        audit_logger.info(f"User: {username} - MAC Trace Started - MAC: {mac_address} - Switches: {len(switches)} - Site: {site}")
        
        # Use ThreadPoolExecutor for concurrent switch processing
        max_workers = min(MAX_WORKERS_PER_SITE, len(switches))  # Don't exceed switch count
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all switch trace tasks
            future_to_switch = {
                executor.submit(trace_single_switch, switch_info, mac_address, username): switch_info
                for switch_info in switches
            }
            
            results = []
            completed_count = 0
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_switch, timeout=60):
                completed_count += 1
                try:
                    result = future.result()
                    results.append(result)
                    
                    # Log progress for large batches
                    if len(switches) > 5:
                        logger.info(f"MAC trace progress: {completed_count}/{len(switches)} switches completed")
                        
                except Exception as e:
                    switch_info = future_to_switch[future]
                    logger.error(f"Error in concurrent trace for {switch_info['name']}: {str(e)}")
                    results.append({
                        'switch_name': switch_info['name'],
                        'switch_ip': switch_info['ip'],
                        'status': 'error',
                        'message': f'Concurrent execution error: {str(e)}'
                    })
        
        elapsed_time = time.time() - start_time
        found_count = len([r for r in results if r['status'] == 'found'])
        
        audit_logger.info(f"User: {username} - MAC Trace Completed - MAC: {mac_address} - Results: {found_count} found - Time: {elapsed_time:.2f}s - Concurrent workers: {max_workers}")
        return results
        
    except concurrent.futures.TimeoutError:
        audit_logger.error(f"User: {username} - MAC Trace TIMEOUT - MAC: {mac_address} - Site: {site}")
        return [{
            'switch_name': 'System',
            'switch_ip': 'N/A',
            'status': 'error',
            'message': 'Trace operation timed out after 60 seconds. Some switches may be unreachable.'
        }]
    except Exception as e:
        audit_logger.error(f"User: {username} - MAC Trace ERROR - MAC: {mac_address} - Site: {site} - Error: {str(e)}")
        return [{
            'switch_name': 'System',
            'switch_ip': 'N/A',
            'status': 'error',
            'message': f'System error during trace: {str(e)}'
        }]
    finally:
        # Always release the concurrent user slot
        release_concurrent_user_slot(site)


# Web Interface HTML Templates
INVENTORY_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Switch Inventory - Dell Port Tracer</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='navigation.css') }}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        .inventory-page {
            background: var(--deep-navy);
            min-height: 100vh;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 0;
        }
        
        .main-content {
            padding: 30px;
            max-width: 1800px;
            margin: 0 auto;
        }
        
        .inventory-layout {
            display: flex;
            height: calc(100vh - 280px);
            overflow: hidden;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
            max-width: 1750px;
            margin: 0 auto;
        }
        
        .sidebar {
            width: 500px;
            background: white;
            border-right: 1px solid #e5e7eb;
            flex-shrink: 0;
            border-radius: 0;
            box-shadow: none;
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        
        .content-area {
            flex: 1;
            background: white;
            overflow-y: auto;
            padding: 20px;
            border-radius: 0;
            box-shadow: none;
        }
        
        /* Duplicate navigation styles removed - using global navigation.css */
        
        /* Sidebar Structure Styles */
        .sidebar-header {
            background: white;
            border-bottom: 1px solid #e5e7eb;
            flex-shrink: 0;
        }
        
        .site-tree-scrollable {
            flex: 1;
            overflow-y: auto;
            background: white;
        }
        
        /* Site Tree Styles */
        .site-tree {
            padding: 20px;
        }
        
        .tree-header .search-box {
            margin-top: 12px;
        }
        
        .tree-header .search-input {
            width: 100%;
            max-width: 280px;
            font-size: 13px;
            padding: 8px 12px;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.9);
        }
        
        .tree-header {
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid var(--orange);
        }
        
        .tree-title {
            font-size: 18px;
            font-weight: 600;
            color: var(--deep-navy);
            margin: 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .tree-item {
            margin-bottom: 8px;
        }
        
        .tree-site {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .site-header {
            padding: 12px 16px;
            background: linear-gradient(135deg, var(--deep-navy), #1e3a8a);
            color: white;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        
        .site-header-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            width: 100%;
        }
        
        .site-left {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .site-right {
            display: flex;
            align-items: center;
            gap: 4px;
            flex-shrink: 0;
            min-width: 0;
        }
        
        .site-stats {
            font-size: 11px;
            opacity: 0.9;
            margin-right: 6px;
            white-space: nowrap;
            flex-shrink: 0;
        }
            display: flex;
            align-items: center;
            gap: 4px;
        }
        
        .site-header:hover {
            background: linear-gradient(135deg, #1e3a8a, var(--orange));
        }
        
        .site-actions {
            display: flex;
            align-items: center;
            gap: 4px;
            flex-shrink: 0;
            white-space: nowrap;
        }
        
        .site-actions .action-btn {
            white-space: nowrap;
            font-size: 9px;
            padding: 2px 6px;
            border: none;
            border-radius: 3px;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            cursor: pointer;
            transition: background-color 0.2s ease;
            min-width: auto;
        }
        
        .site-actions .action-btn:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        
        /* Contextual Floor Actions */
        .floor-actions {
            padding: 8px 16px;
            background: #f1f5f9;
            border-bottom: 1px solid #e2e8f0;
            display: none;
        }
        
        .floor-actions.show {
            display: block;
        }
        
        .floor-actions-buttons {
            display: flex;
            gap: 6px;
            align-items: center;
        }
        
        .floor-action-btn {
            padding: 4px 8px;
            border: 1px solid #64748b;
            background: white;
            color: #64748b;
            border-radius: 4px;
            font-size: 10px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
        }
        
        .floor-action-btn:hover {
            background: var(--orange);
            color: white;
            border-color: var(--orange);
            transform: translateY(-1px);
        }
        
        .floor-actions-label {
            font-size: 10px;
            color: #64748b;
            margin-right: 8px;
            font-weight: 600;
        }
        
        .site-stats {
            font-size: 12px;
            opacity: 0.9;
        }
        
        .expand-icon {
            font-size: 14px;
            transition: transform 0.2s ease;
        }
        
        .site-header.expanded .expand-icon {
            transform: rotate(90deg);
        }
        
        .floors-container {
            display: none;
            background: white;
        }
        
        .floors-container.expanded {
            display: block;
        }
        
        .floor-item {
            border-bottom: 1px solid #f0f0f0;
            padding: 10px 20px;
            cursor: pointer;
            transition: background-color 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .floor-item:last-child {
            border-bottom: none;
        }
        
        .floor-item:hover {
            background: #f8fafc;
        }
        
        .floor-item.selected {
            background: rgba(255, 114, 0, 0.1);
            border-left: 4px solid var(--orange);
            font-weight: 600;
            color: var(--deep-navy);
        }
        
        .floor-name {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .floor-switch-count {
            display: flex;
            align-items: center;
            gap: 4px;
            white-space: nowrap;
        }
        
        .floor-switch-count .action-btn {
            white-space: nowrap;
            font-size: 9px;
            padding: 1px 4px;
            border: 1px solid #64748b;
            background: white;
            color: #64748b;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.2s ease;
            min-width: auto;
            display: inline-flex;
            align-items: center;
            gap: 2px;
        }
        
        .floor-switch-count .action-btn:hover {
            background: var(--orange);
            color: white;
            border-color: var(--orange);
        }
        
        .floor-item.selected .floor-switch-count {
            background: var(--orange);
            color: white;
        }
        
        /* Content Area Styles */
        .content-header {
            background: white;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            border: 1px solid #e5e7eb;
        }
        
        .breadcrumb {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 16px;
            font-size: 14px;
            color: #6b7280;
        }
        
        .breadcrumb-separator {
            color: #d1d5db;
        }
        
        .breadcrumb .current {
            color: var(--orange);
            font-weight: 600;
        }
        
        .floor-title {
            font-size: 24px;
            font-weight: 700;
            color: var(--deep-navy);
            margin: 0 0 8px 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .floor-description {
            color: #6b7280;
            margin: 0;
        }
        
        /* Statistics Cards */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }
        
        .stat-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            border: 1px solid #e5e7eb;
            transition: transform 0.2s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
        }
        
        .stat-number {
            font-size: 32px;
            font-weight: 700;
            margin-bottom: 8px;
        }
        
        .stat-number.total {
            color: var(--orange);
        }
        
        .stat-number.active {
            color: #10b981;
        }
        
        .stat-number.inactive {
            color: #ef4444;
        }
        
        .stat-number.models {
            color: #6366f1;
        }
        
        .stat-label {
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }
        
        /* Switch Table */
        .switches-section {
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            border: 1px solid #e5e7eb;
            overflow: hidden;
        }
        
        .switches-header {
            padding: 20px 24px;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .switches-title {
            font-size: 18px;
            font-weight: 600;
            color: var(--deep-navy);
            margin: 0;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .switches-controls {
            display: flex;
            gap: 12px;
            align-items: center;
            flex-wrap: wrap;
            padding: 16px 0;
        }
        
        /* Standardized Add Switch Button */
        .add-switch-btn {
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 10px 16px;
            background: linear-gradient(135deg, var(--orange), #e68900);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(255, 114, 0, 0.2);
            white-space: nowrap;
            height: 40px;
            min-width: 120px;
            justify-content: center;
            position: relative;
            overflow: hidden;
        }
        
        .add-switch-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, 
                transparent, 
                rgba(255, 255, 255, 0.3), 
                transparent);
            transition: left 0.5s ease;
        }
        
        .add-switch-btn:hover::before {
            left: 100%;
        }
        
        .add-switch-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 16px rgba(255, 114, 0, 0.4);
            filter: brightness(1.1);
        }
        
        .add-switch-btn .btn-icon {
            font-size: 16px;
            font-weight: 700;
        }
        
        /* Standardized Search Box */
        .search-box {
            position: relative;
            flex: 1;
            max-width: 300px;
            min-width: 200px;
        }
        
        .search-input {
            width: 100%;
            padding: 10px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 8px;
            font-size: 14px;
            background-color: white;
            transition: all 0.3s ease;
            box-sizing: border-box;
            height: 40px;
        }
        
        .search-input:focus {
            outline: none;
            border-color: var(--orange);
            box-shadow: 0 0 0 3px rgba(255, 114, 0, 0.1);
        }
        
        .search-input::placeholder {
            color: #9ca3af;
            font-size: 14px;
        }
        
        /* Filter Buttons Container */
        .filter-buttons {
            display: flex;
            gap: 4px;
            align-items: center;
        }
        
        /* Standardized Filter Buttons */
        .filter-btn {
            padding: 10px 16px;
            border: 2px solid #e5e7eb;
            background: white;
            color: #374151;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            height: 40px;
            min-width: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .filter-btn:hover {
            border-color: var(--orange);
            color: var(--orange);
            background: rgba(255, 114, 0, 0.05);
            transform: translateY(-1px);
        }
        
        .filter-btn.active {
            background: var(--orange);
            color: white;
            border-color: var(--orange);
            box-shadow: 0 2px 8px rgba(255, 114, 0, 0.2);
        }
        
        .filter-btn.active:hover {
            background: #e68900;
            border-color: #e68900;
        }
        
        /* Sidebar Search Styling */
        .tree-header .search-box {
            margin-top: 12px;
            max-width: none;
            min-width: auto;
        }
        
        .tree-header .search-input {
            font-size: 13px;
            padding: 8px 12px;
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.9);
            height: 36px;
        }
        
        /* Management Buttons in Sidebar */
        .management-buttons {
            display: flex;
            gap: 8px;
            margin: 12px 0;
            flex-wrap: wrap;
        }
        
        .management-buttons .action-btn {
            padding: 8px 12px;
            border: 1px solid var(--orange);
            background: var(--orange);
            color: white;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
            height: 32px;
            display: flex;
            align-items: center;
        }
        
        .management-buttons .action-btn:hover {
            background: #e68900;
            border-color: #e68900;
            transform: translateY(-1px);
        }
        
        .switches-table {
            width: 100%;
            border-collapse: collapse;
        }
        
        .switches-table th {
            background: #f8fafc;
            color: #374151;
            font-weight: 600;
            padding: 12px 16px;
            text-align: left;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #e5e7eb;
        }
        
        .switches-table td {
            padding: 16px;
            border-bottom: 1px solid #f0f0f0;
            vertical-align: middle;
        }
        
        .switches-table tr:last-child td {
            border-bottom: none;
        }
        
        .switches-table tr:hover {
            background: #f8fafc;
        }
        
        .switch-name {
            font-weight: 600;
            color: var(--deep-navy);
            margin-bottom: 4px;
        }
        
        .switch-model {
            font-size: 12px;
            color: #6b7280;
        }
        
        .switch-ip {
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #374151;
        }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        
        .status-active {
            background: #dcfce7;
            color: #166534;
        }
        
        .status-inactive {
            background: #fecaca;
            color: #991b1b;
        }
        
        .switch-actions {
            display: flex;
            gap: 6px;
        }
        
        .action-btn {
            padding: 6px 10px;
            border: 1px solid #d1d5db;
            border-radius: 4px;
            background: white;
            color: #374151;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        
        .action-btn:hover {
            border-color: var(--orange);
            color: var(--orange);
        }
        
        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            color: #6b7280;
        }
        
        .empty-icon {
            font-size: 48px;
            margin-bottom: 16px;
            opacity: 0.5;
        }
        
        .empty-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .empty-description {
            font-size: 14px;
            margin: 0;
        }
        
        /* Loading State */
        .loading-state {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 40px;
            color: #6b7280;
        }
        
        .loading-spinner {
            width: 20px;
            height: 20px;
            border: 2px solid #e5e7eb;
            border-top: 2px solid var(--orange);
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin-right: 12px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        /* Modal Styles */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            backdrop-filter: blur(2px);
        }
        
        .modal-content {
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
            max-width: 450px;
            width: 90%;
            max-height: 85vh;
            overflow-y: auto;
        }
        
        .modal-header {
            padding: 16px 20px;
            border-bottom: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .modal-header h3 {
            margin: 0;
            color: var(--deep-navy);
            font-size: 18px;
            font-weight: 600;
        }
        
        .modal-close {
            background: none;
            border: none;
            font-size: 24px;
            color: #6b7280;
            cursor: pointer;
            padding: 0;
            width: 30px;
            height: 30px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            transition: all 0.2s ease;
        }
        
        .modal-close:hover {
            background: #f3f4f6;
            color: #374151;
        }
        
        .modal-body {
            padding: 16px 20px;
        }
        
        .modal-body .form-group {
            margin-bottom: 12px;
        }
        
        .modal-body .form-group label {
            display: block;
            margin-bottom: 4px;
            font-weight: 600;
            color: var(--deep-navy);
            font-size: 13px;
        }
        
        .modal-body .form-group input,
        .modal-body .form-group select {
            width: 100%;
            padding: 8px 10px;
            border: 1px solid #e1e8ed;
            border-radius: 6px;
            font-size: 14px;
            transition: all 0.2s ease;
            background: white;
            box-sizing: border-box;
        }
        
        .modal-body .form-group input:focus,
        .modal-body .form-group select:focus {
            outline: none;
            border-color: var(--orange);
            box-shadow: 0 0 0 3px rgba(255, 114, 0, 0.1);
        }
        
        .modal-body .form-group input[readonly] {
            background: #f9fafb;
            color: #6c757d;
        }
        
        .modal-body .checkbox-group {
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 8px 0;
        }
        
        .modal-body .checkbox-group input[type="checkbox"] {
            width: 16px;
            height: 16px;
            margin: 0;
            accent-color: var(--orange);
        }
        
        .modal-body .checkbox-group label {
            margin: 0;
            font-size: 14px;
            cursor: pointer;
        }
        
        .modal-body .form-actions {
            display: flex;
            gap: 8px;
            margin-top: 16px;
            padding-top: 12px;
            border-top: 1px solid #e5e7eb;
            flex-wrap: nowrap;
            align-items: center;
        }
        
        /* Delete Confirmation Modal */
        .delete-modal .modal-content {
            max-width: 450px;
        }
        
        .delete-modal .modal-header {
            background: linear-gradient(135deg, #fee2e2, #fca5a5);
            border-bottom: 1px solid #f87171;
        }
        
        .delete-modal .modal-header h3 {
            color: #dc2626;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .delete-warning {
            background: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 16px;
            margin: 16px 0;
        }
        
        .delete-warning-title {
            font-weight: 600;
            color: #dc2626;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .delete-warning-text {
            color: #7f1d1d;
            font-size: 14px;
            line-height: 1.5;
            margin-bottom: 8px;
        }
        
        .delete-item-name {
            font-weight: 600;
            color: #991b1b;
        }
        
        .delete-actions {
            display: flex;
            gap: 8px;
            justify-content: flex-end;
            margin-top: 20px;
            flex-wrap: nowrap;
            align-items: center;
        }
        
        .btn-cancel {
            padding: 8px 16px;
            background: #f9fafb;
            color: #374151;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
            display: inline-block;
        }
        
        .btn-cancel:hover {
            background: #e5e7eb;
            border-color: #9ca3af;
        }
        
        .btn-delete {
            padding: 8px 16px;
            background: linear-gradient(135deg, #dc2626, #b91c1c);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(220, 38, 38, 0.2);
            white-space: nowrap;
            display: inline-block;
        }
        
        .btn-delete:hover {
            background: linear-gradient(135deg, #b91c1c, #991b1b);
            box-shadow: 0 4px 8px rgba(220, 38, 38, 0.3);
            transform: translateY(-1px);
        }
            padding-top: 16px;
            border-top: 1px solid #e1e8ed;
        }
        
        .modal-body .btn-primary {
            background: var(--orange);
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
            display: inline-block;
            min-width: 80px;
            text-align: center;
        }
        
        .modal-body .btn-primary:hover {
            background: #e68900;
        }
        
        .modal-body .btn-secondary {
            background: #6c757d;
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
            display: inline-block;
            min-width: 80px;
            text-align: center;
        }
        
        .modal-body .btn-secondary:hover {
            background: #5a6268;
        }
        
        .modal-body .btn-danger {
            background: linear-gradient(135deg, #dc2626, #b91c1c);
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
            display: inline-block;
            min-width: 80px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(220, 38, 38, 0.2);
        }
        
        .modal-body .btn-danger:hover {
            background: linear-gradient(135deg, #b91c1c, #991b1b);
            box-shadow: 0 4px 8px rgba(220, 38, 38, 0.3);
            transform: translateY(-1px);
        }
        
        /* UI CONSISTENCY IMPROVEMENT (January 2025)
         * Standardized button sizing across all modal dialogs
         * 
         * PROBLEM SOLVED: Edit site/floor modals had inconsistent button sizes
         * - Update and Delete buttons were larger than Cancel button
         * - Inconsistent padding, width, and visual appearance
         * 
         * SOLUTION: Comprehensive button standardization with !important declarations
         * - All modal form action buttons now have identical dimensions
         * - Consistent 80px minimum width for professional appearance
         * - Unified padding, font size, and styling across all button types
         * - Prevents text wrapping with white-space: nowrap
         * - Applies to Update (btn-primary), Delete (btn-danger), Cancel (btn-secondary)
         */
        .modal-body .form-actions button {
            min-width: 80px !important;        /* Consistent minimum width */
            text-align: center !important;     /* Center button text */
            padding: 8px 12px !important;      /* Uniform padding */
            border-radius: 6px !important;     /* Consistent border radius */
            font-size: 12px !important;        /* Standardized font size */
            font-weight: 500 !important;       /* Consistent font weight */
            cursor: pointer !important;        /* Ensure pointer cursor */
            transition: all 0.2s ease !important; /* Smooth hover effects */
            white-space: nowrap !important;     /* Prevent text wrapping */
            display: inline-block !important;   /* Consistent display type */
        }
        
        /* Toast Styles */
        .toast {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 20px;
            border-radius: 8px;
            color: white;
            z-index: 1100;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            max-width: 400px;
            font-size: 14px;
        }
        
        .toast.show {
            opacity: 1;
            transform: translateX(0);
        }
        
        .toast.success {
            background: linear-gradient(135deg, #28a745, #20c997);
        }
        
        .toast.error {
            background: linear-gradient(135deg, #dc3545, #e74c3c);
        }
        
        /* Responsive Design */
        @media (max-width: 1024px) {
            .main-content {
                flex-direction: column;
                height: auto;
                width: calc(100vw - 20px);
                padding: 30px 10px 20px 10px;
            }
            
            .sidebar {
                width: 100%;
                height: 300px;
            }
            
            .content-area {
                height: auto;
            }
        }
        
        @media (max-width: 768px) {
            .switches-controls {
                flex-direction: column;
                align-items: stretch;
                gap: 8px;
            }
            
            .search-input {
                width: 100%;
            }
            
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body class="inventory-page">
        <div class="main-content">
            <div class="header-card">
                <div class="logo-section">
                    <img src="{{ url_for('static', filename='img/kmc_logo.png') }}" alt="KMC Logo">
                    <h1 class="app-title">Switch Port Tracer</h1>
                </div>
                <div class="user-profile">
                    <div class="user-avatar">{{ username[0].upper() }}</div>
                    <div class="user-details">
                        <div class="username">{{ username }}</div>
                        <div class="user-role">{{ user_role }}</div>
                    </div>
                    <a href="/logout" class="logout-btn">Logout</a>
                </div>
            </div>
            
            <div class="navigation-card">
                <div class="nav-links">
                    <a href="/" class="nav-link">🔍 Port Tracer</a>
                    {% if user_role in ['netadmin', 'superadmin'] %}
                    <a href="/vlan" class="nav-link">🔧 VLAN Manager</a>
                    <a href="/inventory" class="nav-link active">🏢 Switch Management</a>
                    {% endif %}
                </div>
            </div>

            <div class="inventory-layout">
                <!-- Sidebar with Site Tree -->
                <div class="sidebar">
                    <div class="sidebar-header">
                        <div class="site-tree">
                            <div class="tree-header">
                                <h2 class="tree-title">
                                    <span>🏢</span>
                                    KMC Sites
                                </h2>
                                
                                <div class="management-buttons">
                                    <button class="action-btn" onclick="showAddSiteModal()" title="Add new site">
                                        + Add Site
                                    </button>
                                    <button class="action-btn" id="add-floor-btn" onclick="showAddFloorModal()" title="Add floor to selected site" style="display: none;">
                                        + Add Floor
                                    </button>
                                </div>
                                
                                <div class="search-box">
                                    <input type="text" class="search-input" id="site-search" placeholder="Search sites and floors...">
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="site-tree-scrollable">
                        <div class="site-tree">
                            <div id="site-tree-container">
                                <div class="loading-state">
                                    <div class="loading-spinner"></div>
                                    Loading sites...
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Main Content Area -->
                <div class="content-area">
            <div class="content-header">
                <div class="breadcrumb">
                    <span>🏢 Sites</span>
                    <span class="breadcrumb-separator">›</span>
                    <span id="current-site">Select a site</span>
                    <span class="breadcrumb-separator" id="floor-separator" style="display: none;">›</span>
                    <span class="current" id="current-floor" style="display: none;">Select a floor</span>
                </div>
                
                <h1 class="floor-title" id="content-title">
                    <span>📋</span>
                    Switch Inventory
                </h1>
                
                <p class="floor-description" id="content-description">
                    Select a site and floor from the left sidebar to view switch inventory
                </p>
            </div>
            
            <!-- Statistics Cards -->
            <div class="stats-grid" id="stats-grid" style="display: none;">
                <div class="stat-card">
                    <div class="stat-number total" id="total-switches">0</div>
                    <div class="stat-label">Total Switches</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number active" id="active-switches">0</div>
                    <div class="stat-label">Active Switches</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number inactive" id="inactive-switches">0</div>
                    <div class="stat-label">Inactive Switches</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number models" id="unique-models">0</div>
                    <div class="stat-label">Switch Models</div>
                </div>
            </div>
            
            <!-- Switches Section -->
            <div class="switches-section" id="switches-section">
                <div class="switches-header">
                    <h3 class="switches-title">
                        <span>🔌</span>
                        Switch Details
                    </h3>
                    
                        <div class="switches-controls" id="switches-controls" style="display: none;">
                            <button class="add-switch-btn" id="add-switch-btn" onclick="showAddSwitchToFloorModal()" title="Add switch to selected floor" style="display: none;">
                                <span class="btn-icon">+</span> Add Switch
                            </button>
                            <div class="search-box">
                                <input type="text" class="search-input" id="switch-search" placeholder="Search switches...">
                            </div>
                            <div class="filter-buttons">
                                <button class="filter-btn active" data-filter="all">All</button>
                                <button class="filter-btn" data-filter="active">Active</button>
                                <button class="filter-btn" data-filter="inactive">Inactive</button>
                            </div>
                        </div>
                </div>
                
                <div id="switches-content">
                    <div class="empty-state">
                        <div class="empty-icon">🔍</div>
                        <div class="empty-title">No Floor Selected</div>
                        <div class="empty-description">Choose a site and floor from the sidebar to view switch inventory</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let sitesData = [];
        let currentSiteData = null;
        let currentFloorData = null;
        let allSwitches = [];
        let filteredSwitches = [];
        
        // Add switch to floor from main inventory view - GLOBAL FUNCTION
        function showAddSwitchToFloorModal() {
            console.log('showAddSwitchToFloorModal called');
            console.log('currentFloorData:', currentFloorData);
            console.log('currentSiteData:', currentSiteData);
            
            // Check if we have current floor data from inventory view
            if (typeof currentFloorData !== 'undefined' && currentFloorData && currentFloorData.id) {
                console.log('Using currentFloorData for modal');
                // Use current floor data from inventory
                if (typeof openAddSwitchModalWithFloor === 'function') {
                    openAddSwitchModalWithFloor(
                        currentFloorData.id, 
                        currentFloorData.name, 
                        currentSiteData ? currentSiteData.name : 'Unknown Site'
                    );
                } else {
                    console.error('openAddSwitchModalWithFloor function not available');
                    alert('Error: Modal function not available');
                }
            } else {
                console.log('currentFloorData not available, showing generic modal');
                // Show generic add switch modal that allows selection of site and floor
                if (typeof showGenericAddSwitchModal === 'function') {
                    showGenericAddSwitchModal();
                } else {
                    alert('Please select a floor first');
                }
            }
        }
        
        // Make the function globally available
        window.showAddSwitchToFloorModal = showAddSwitchToFloorModal;
        
        // Initialize the application
        document.addEventListener('DOMContentLoaded', function() {
            // Hide Add Switch button initially since no floor is selected
            const addSwitchBtn = document.getElementById('add-switch-btn');
            if (addSwitchBtn) {
                addSwitchBtn.style.display = 'none';
            }
            
            loadSites();
            setupEventListeners();
        });
        
        // Setup event listeners
        function setupEventListeners() {
            // Search functionality
            document.getElementById('switch-search').addEventListener('input', handleSearchInput);
            
            // Filter buttons
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.addEventListener('click', handleFilterClick);
            });
        }
        
        // Load sites from API
        async function loadSites() {
            try {
                const response = await fetch('/api/sites');
                const data = await response.json();
                
                if (response.ok) {
                    sitesData = data;
                    // Load all switches data first for counting
                    await loadAllSwitches();
                    renderSiteTree(data);
                } else {
                    showError('Failed to load sites: ' + data.error);
                }
            } catch (error) {
                showError('Error loading sites: ' + error.message);
            }
        }
        
        // Load all switches for site counting
        async function loadAllSwitches() {
            try {
                const response = await fetch('/api/switches');
                const data = await response.json();
                
                if (response.ok) {
                    allSwitches = data; // Store all switches globally
                } else {
                    console.error('Failed to load all switches:', data.error);
                    allSwitches = [];
                }
            } catch (error) {
                console.error('Error loading all switches:', error.message);
                allSwitches = [];
            }
        }
        
        // Render the site tree
        function renderSiteTree(sites) {
            const container = document.getElementById('site-tree-container');
            
            if (sites.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">🏢</div>
                        <div class="empty-title">No Sites Found</div>
                        <div class="empty-description">No sites are configured in the system</div>
                    </div>
                `;
                return;
            }
            
            let html = '';
            sites.forEach(site => {
                // Calculate total switches properly from database structure
                let totalSwitches = 0;
                if (site.floors && Array.isArray(site.floors)) {
                    // Count switches across all floors for this site
                    site.floors.forEach(floor => {
                        // Count switches from the global allSwitches array for this floor
                        if (typeof allSwitches !== 'undefined' && allSwitches.length > 0) {
                            const floorSwitches = allSwitches.filter(sw => sw.floor_id == floor.id);
                            totalSwitches += floorSwitches.length;
                        }
                    });
                }
                
                // Debug logging for switch count calculation
                console.log(`Site ${site.name}: ${totalSwitches} switches calculated from allSwitches array`);
                
                const floorCount = site.floors ? site.floors.length : 0;
                
                // Escape single quotes in site name for onclick handlers
                const escapedName = site.name.replace(/'/g, "\\'");
                html += `
                    <div class="tree-item">
                        <div class="tree-site">
                            <div class="site-header" onclick="toggleSite('${site.id}')" id="site-header-${site.id}">
                                <div class="site-header-content">
                                    <div class="site-left">
                                        <span>🏢</span>
                                        <span>${site.name}</span>
                                    </div>
                                    <div class="site-right">
                                        <div class="site-stats">
                                            <span>${floorCount} floors • ${totalSwitches} switches</span>
                                        </div>
                                        <div class="site-actions">
                                            <button class="action-btn" onclick="event.stopPropagation(); editSite(${site.id}, '${escapedName}')" 
                                                title="Edit site">
                                                ✏️
                                            </button>
                                            <div class="expand-icon">▶</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="floors-container" id="floors-${site.id}">
                                ${renderFloors(site.floors, site.id, site.name)}
                            </div>
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        }
        
        // Helper function to format floor names with 'F' prefix for numeric floors
        function formatFloorName(floorName) {
            // Check if floor name is just a number (like "1", "2", "11", etc.)
            if (/^\\d+$/.test(floorName)) {
                return `F${floorName}`;
            }
            // For non-numeric floors like "GF", "PH", "B1", etc., return as-is
            return floorName;
        }
        
        // Render floors for a site
        function renderFloors(floors, siteId, siteName) {
            if (floors.length === 0) {
                return '<div class="floor-item"><div class="floor-name">No floors configured</div></div>';
            }
            
            return floors.map(floor => {
                // Escape single quotes in floor name for onclick handlers
                const escapedName = floor.name.replace(/'/g, "\\'");
                const displayName = formatFloorName(floor.name);
                return `
                    <div class="floor-item" onclick="selectFloor('${siteId}', '${siteName}', '${floor.id}', '${floor.name}')" id="floor-${floor.id}">
                        <div class="floor-name">
                            <span>🏢</span>
                            <span>${displayName}</span>
                        </div>
                        <div class="floor-switch-count">
                            <button class="action-btn" onclick="event.stopPropagation(); editFloor(${floor.id}, '${escapedName}', ${siteId})" 
                                title="Edit floor">
                                ✏️
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        // Toggle site expansion and select site
        function toggleSite(siteId) {
            const header = document.getElementById(`site-header-${siteId}`);
            const floors = document.getElementById(`floors-${siteId}`);
            const expandIcon = header.querySelector('.expand-icon');
            
            // First, select this site (remove selection from other sites)
            document.querySelectorAll('.site-header').forEach(el => {
                el.classList.remove('selected');
            });
            header.classList.add('selected');
            
            // Store the selected site globally - get site name from sitesData array
            const siteData = sitesData.find(site => site.id == siteId);
            const siteName = siteData ? siteData.name : 'Unknown Site';
            window.selectedSiteId = siteId;
            window.selectedSiteName = siteName;
            
            // Clear any floor selection and hide Add Switch button
            document.querySelectorAll('.floor-item').forEach(item => {
                item.classList.remove('selected');
            });
            currentFloorData = null;
            
            // Hide the Add Switch button since no specific floor is selected
            const addSwitchBtn = document.getElementById('add-switch-btn');
            if (addSwitchBtn) {
                addSwitchBtn.style.display = 'none';
            }
            
            // Load all switches for this site
            loadSiteSwitches(siteId, siteName);
            
            // Show Add Floor button since site is selected
            showAddFloorButton(siteId);
            
            const isExpanded = floors.classList.contains('expanded');
            
            if (isExpanded) {
                floors.classList.remove('expanded');
                header.classList.remove('expanded');
            } else {
                // Close other expanded sites first
                document.querySelectorAll('.floors-container').forEach(el => {
                    el.classList.remove('expanded');
                });
                document.querySelectorAll('.site-header').forEach(el => {
                    if (el !== header) {
                        el.classList.remove('expanded');
                    }
                });
                
                floors.classList.add('expanded');
                header.classList.add('expanded');
            }
        }
        
        // Show Add Floor button for a specific site
        function showAddFloorButton(siteId) {
            const addFloorBtn = document.getElementById('add-floor-btn');
            if (addFloorBtn) {
                addFloorBtn.style.display = 'inline-block';
                // Store the currently selected site ID for the Add Floor functionality
                addFloorBtn.setAttribute('data-site-id', siteId);
            }
        }
        
        // Hide Add Floor button
        function hideAddFloorButton() {
            const addFloorBtn = document.getElementById('add-floor-btn');
            if (addFloorBtn) {
                addFloorBtn.style.display = 'none';
                addFloorBtn.removeAttribute('data-site-id');
            }
        }
        
        // Select a floor and load its switches
        async function selectFloor(siteId, siteName, floorId, floorName) {
            // Update selection state
            document.querySelectorAll('.floor-item').forEach(item => {
                item.classList.remove('selected');
            });
            document.getElementById(`floor-${floorId}`).classList.add('selected');
            
            // Update breadcrumb and title
            updateContentHeader(siteName, floorName);
            
            // Store current selection
            currentSiteData = { id: siteId, name: siteName };
            currentFloorData = { id: floorId, name: floorName };
            
            // Show the Add Switch button since a floor is now selected
            const addSwitchBtn = document.getElementById('add-switch-btn');
            if (addSwitchBtn) {
                addSwitchBtn.style.display = 'flex';
            }
            
            // Load switches for this floor
            await loadFloorSwitches(floorId);
        }
        
        // Update content header for floor view
        function updateContentHeader(siteName, floorName) {
            const displayFloorName = formatFloorName(floorName);
            document.getElementById('current-site').textContent = siteName;
            document.getElementById('current-floor').textContent = displayFloorName;
            document.getElementById('current-floor').style.display = 'inline';
            document.getElementById('floor-separator').style.display = 'inline';
            
            document.getElementById('content-title').innerHTML = `
                <span>🏢</span>
                ${displayFloorName} - Switch Inventory
            `;
            
            document.getElementById('content-description').textContent = 
                `Viewing switches for ${displayFloorName} in ${siteName}`;
        }
        
        // Update content header for site view (all floors)
        function updateSiteContentHeader(siteName) {
            document.getElementById('current-site').textContent = siteName;
            document.getElementById('current-floor').style.display = 'none';
            document.getElementById('floor-separator').style.display = 'none';
            
            document.getElementById('content-title').innerHTML = `
                <span>🏢</span>
                ${siteName} - Switch Inventory
            `;
            
            document.getElementById('content-description').textContent = 
                `Viewing all switches for ${siteName} (aggregated across all floors)`;
        }
        
        // Load all switches for a specific site
        async function loadSiteSwitches(siteId, siteName) {
            try {
                // Show loading state
                document.getElementById('switches-content').innerHTML = `
                    <div class="loading-state">
                        <div class="loading-spinner"></div>
                        Loading switches for ${siteName}...
                    </div>
                `;
                
                const response = await fetch('/api/switches');
                const data = await response.json();
                
                if (response.ok) {
                    // Filter switches for all floors in this site
                    allSwitches = data.filter(sw => sw.site_id == siteId);
                    filteredSwitches = [...allSwitches];
                    
                    // Update breadcrumb and header for site view
                    updateSiteContentHeader(siteName);
                    
                    renderSwitches();
                    updateStats();
                    
                    // Show controls
                    document.getElementById('switches-controls').style.display = 'flex';
                    document.getElementById('stats-grid').style.display = 'grid';
                } else {
                    showError('Failed to load switches: ' + data.error);
                }
            } catch (error) {
                showError('Error loading switches: ' + error.message);
            }
        }
        
        // Load switches for a specific floor
        async function loadFloorSwitches(floorId) {
            try {
                // Show loading state
                document.getElementById('switches-content').innerHTML = `
                    <div class="loading-state">
                        <div class="loading-spinner"></div>
                        Loading switches...
                    </div>
                `;
                
                const response = await fetch('/api/switches');
                const data = await response.json();
                
                if (response.ok) {
                    // Filter switches for this floor
                    allSwitches = data.filter(sw => sw.floor_id == floorId);
                    filteredSwitches = [...allSwitches];
                    
                    renderSwitches();
                    updateStats();
                    
                    // Show controls
                    document.getElementById('switches-controls').style.display = 'flex';
                    document.getElementById('stats-grid').style.display = 'grid';
                } else {
                    showError('Failed to load switches: ' + data.error);
                }
            } catch (error) {
                showError('Error loading switches: ' + error.message);
            }
        }
        
        // Render switches table with proper filtering
        function renderSwitches(switchesToRender = null) {
            const content = document.getElementById('switches-content');
            const switches = switchesToRender || filteredSwitches || allSwitches || [];
            
            if (switches.length === 0) {
                content.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">🔌</div>
                        <div class="empty-title">No Switches Found</div>
                        <div class="empty-description">No switches match the current filter criteria</div>
                    </div>
                `;
                return;
            }
            
            let html = `
                <table class="switches-table">
                    <thead>
                        <tr>
                            <th>Switch Name</th>
                            <th>Model</th>
                            <th>IP Address</th>
                            <th>Status</th>
                            <th>Description</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            switches.forEach(sw => {
                const statusClass = sw.enabled ? 'active' : 'inactive';
                const statusIcon = sw.enabled ? '✅' : '❌';
                const statusText = sw.enabled ? 'Active' : 'Inactive';
                
                html += `
                    <tr>
                        <td>
                            <div class="switch-name">${sw.name}</div>
                        </td>
                        <td>${sw.model}</td>
                        <td><code class="switch-ip">${sw.ip_address}</code></td>
                        <td>
                            <span class="status-badge status-${statusClass}">
                                <span>${statusIcon}</span>
                                ${statusText}
                            </span>
                        </td>
                        <td>${sw.description || '-'}</td>
                        <td>
                            <div class="switch-actions">
                                <button class="action-btn" onclick="editSwitch(${sw.id})" title="Edit switch">
                                    ✏️ Edit
                                </button>
                                <button class="action-btn" onclick="deleteSwitch(${sw.id}, '${sw.name.replace(/'/g, "\\'")}')"
                                    title="Delete switch" style="color: #dc3545; border-color: #dc3545;">
                                    🗑️ Delete
                                </button>
                            </div>
                        </td>
                    </tr>
                `;
            });
            
            html += `
                    </tbody>
                </table>
            `;
            
            content.innerHTML = html;
        }
        
        // Update statistics
        function updateStats() {
            const total = allSwitches.length;
            const active = allSwitches.filter(sw => sw.enabled).length;
            const inactive = total - active;
            const models = new Set(allSwitches.map(sw => sw.model)).size;
            
            document.getElementById('total-switches').textContent = total;
            document.getElementById('active-switches').textContent = active;
            document.getElementById('inactive-switches').textContent = inactive;
            document.getElementById('unique-models').textContent = models;
        }
        
        // Handle search input
        function handleSearchInput(event) {
            const query = event.target.value.toLowerCase();
            
            filteredSwitches = allSwitches.filter(sw => 
                sw.name.toLowerCase().includes(query) ||
                sw.model.toLowerCase().includes(query) ||
                sw.ip_address.toLowerCase().includes(query) ||
                (sw.description && sw.description.toLowerCase().includes(query)) ||
                (sw.site_name && sw.site_name.toLowerCase().includes(query)) ||
                (sw.floor_name && sw.floor_name.toLowerCase().includes(query))
            );
            
            renderSwitches();
        }
        
        // Handle filter button clicks
        function handleFilterClick(event) {
            const filter = event.target.dataset.filter;
            
            // Update active filter button
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Apply filter
            switch (filter) {
                case 'all':
                    filteredSwitches = [...allSwitches];
                    break;
                case 'active':
                    filteredSwitches = allSwitches.filter(sw => sw.enabled);
                    break;
                case 'inactive':
                    filteredSwitches = allSwitches.filter(sw => !sw.enabled);
                    break;
            }
            
            // Apply current search if any
            const searchQuery = document.getElementById('switch-search').value.toLowerCase();
            if (searchQuery) {
                filteredSwitches = filteredSwitches.filter(sw => 
                    sw.name.toLowerCase().includes(searchQuery) ||
                    sw.model.toLowerCase().includes(searchQuery) ||
                    sw.ip_address.toLowerCase().includes(searchQuery) ||
                    (sw.description && sw.description.toLowerCase().includes(searchQuery))
                );
            }
            
            renderSwitches();
        }
        
        // Switch action functions
        function viewSwitchDetails(switchId) {
            const sw = allSwitches.find(s => s.id === switchId);
            if (sw) {
                alert(`Switch Details:\n\nName: ${sw.name}\nModel: ${sw.model}\nIP: ${sw.ip_address}\nStatus: ${sw.enabled ? 'Active' : 'Inactive'}\nDescription: ${sw.description || 'None'}`);
            }
        }
        
        function editSwitch(switchId) {
            // Find the switch data
            const switchData = allSwitches.find(sw => sw.id == switchId);
            if (!switchData) {
                showError('Switch not found');
                return;
            }
            
            // Open edit modal instead of redirecting
            showEditSwitchModal(switchData);
        }
        
        // Site search functionality
        document.getElementById('site-search').addEventListener('input', function(e) {
            const searchTerm = e.target.value.toLowerCase();
            const siteItems = document.querySelectorAll('.tree-site');
            
            // If clearing search (empty term), collapse all sites (default behavior)
            if (!searchTerm) {
                siteItems.forEach(siteItem => {
                    const floorsContainer = siteItem.querySelector('.floors-container');
                    const siteHeader = siteItem.querySelector('.site-header');
                    
                    // Show all sites and floors
                    siteItem.parentElement.style.display = 'block';
                    siteItem.querySelectorAll('.floor-item').forEach(floor => {
                        floor.style.display = 'flex';
                    });
                    
                    // Default behavior: collapse all sites when clearing search
                    floorsContainer.classList.remove('expanded');
                    siteHeader.classList.remove('expanded');
                });
                return;
            }
            
            siteItems.forEach(siteItem => {
                // Fix: Use correct selector path for site name
                const siteNameElement = siteItem.querySelector('.site-header-content .site-left span:nth-child(2)');
                if (!siteNameElement) return; // Skip if element not found
                
                const siteName = siteNameElement.textContent.toLowerCase();
                const floorItems = siteItem.querySelectorAll('.floor-item');
                let hasVisibleFloors = false;
                
                // Filter floors within each site
                floorItems.forEach(floorItem => {
                    const floorNameElement = floorItem.querySelector('.floor-name span:nth-child(2)');
                    if (!floorNameElement) return; // Skip if element not found
                    
                    const floorName = floorNameElement.textContent.toLowerCase();
                    const shouldShow = siteName.includes(searchTerm) || floorName.includes(searchTerm);
                    floorItem.style.display = shouldShow ? 'flex' : 'none';
                    if (shouldShow) hasVisibleFloors = true;
                });
                
                // Show/hide entire site based on search
                const shouldShowSite = siteName.includes(searchTerm) || hasVisibleFloors;
                siteItem.parentElement.style.display = shouldShowSite ? 'block' : 'none';
                
                // Auto-expand sites that match search
                if (searchTerm && shouldShowSite) {
                    const floorsContainer = siteItem.querySelector('.floors-container');
                    const siteHeader = siteItem.querySelector('.site-header');
                    if (floorsContainer && siteHeader) {
                        floorsContainer.classList.add('expanded');
                        siteHeader.classList.add('expanded');
                    }
                }
            });
        });
        
        // Modal functions
        function showAddSiteModal() {
            const modal = createModal('Add Site', `
                <form id="add-site-form">
                    <div class="form-group">
                        <label for="new-site-name">Site Name</label>
                            <input type="text" id="new-site-name" name="name" required placeholder="e.g., NYC_MAIN" maxlength="50" 
                               pattern="^[A-Za-z0-9_-]+$" 
                               title="Only letters, numbers, underscores, and hyphens allowed. No spaces or special characters.">
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">💾 Create Site</button>
                        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
                    </div>
                </form>
            `);
            
            document.getElementById('add-site-form').addEventListener('submit', handleAddSite);
        }
        
        function showAddFloorModal() {
            // Check if a site is selected either through site selection or floor selection
            let selectedSiteId = null;
            let selectedSiteName = null;
            
            if (currentSiteData) {
                // Floor was selected, use currentSiteData
                selectedSiteId = currentSiteData.id;
                selectedSiteName = currentSiteData.name;
            } else if (window.selectedSiteId && window.selectedSiteName) {
                // Only site was selected, use global selection
                selectedSiteId = window.selectedSiteId;
                selectedSiteName = window.selectedSiteName;
            }
            
            if (!selectedSiteId) {
                showToast('Please select a site first', 'error');
                return;
            }
            
            const modal = createModal('Add Floor', `
                <form id="add-floor-form">
                    <input type="hidden" id="floor-site-id" value="${selectedSiteId}">
                    <div class="form-group">
                        <label for="floor-site-name">Site</label>
                        <input type="text" id="floor-site-name" value="${selectedSiteName}" readonly>
                    </div>
                    <div class="form-group">
                        <label for="new-floor-name">Floor Name</label>
                        <input type="text" id="new-floor-name" name="name" required placeholder="e.g., Floor 1 or F1 or GF" maxlength="20" 
                               pattern="^(F[0-9]{1,2}|GF|PH|B[0-9]|Floor [0-9]{1,2}|[0-9]{1,2}|Ground Floor|Penthouse|Basement)$" 
                               title="Valid formats: F1-F99, GF, PH, B1-B9, Floor 1-99, 1-99, Ground Floor, Penthouse, or Basement">
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">💾 Create Floor</button>
                        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
                    </div>
                </form>
            `);
            
            document.getElementById('add-floor-form').addEventListener('submit', handleAddFloor);
        }
        
        function showEditSwitchModal(switchData) {
            const modal = createModal('Edit Switch', `
                <form id="edit-switch-form">
                    <input type="hidden" id="edit-switch-id" value="${switchData.id}">
                    <div class="form-group">
                        <label for="edit-switch-name">Switch Name</label>
                        <input type="text" id="edit-switch-name" value="${switchData.name}" required maxlength="50" 
                               pattern="[A-Za-z0-9_-]+" 
                               title="Only letters, numbers, underscores, and hyphens allowed. Format: SITE-FLOOR-RACK-TYPE-NUMBER">
                    </div>
                    <div class="form-group">
                        <label for="edit-switch-ip">IP Address</label>
                        <input type="text" id="edit-switch-ip" value="${switchData.ip_address}" required 
                               pattern="^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$" 
                               title="Valid IPv4 address required (e.g., 192.168.1.100)">
                    </div>
                        <div class="form-group">
                            <label for="edit-switch-model">Model</label>
                            <select id="edit-switch-model" required>
                                <option value="">Select switch model...</option>
                                <optgroup label="Dell N2000 Series">
                                    <option value="Dell N2024" ${switchData.model === 'Dell N2024' ? 'selected' : ''}>Dell N2024</option>
                                    <option value="Dell N2048" ${switchData.model === 'Dell N2048' ? 'selected' : ''}>Dell N2048</option>
                                    <option value="Dell N2048P" ${switchData.model === 'Dell N2048P' ? 'selected' : ''}>Dell N2048P</option>
                                </optgroup>
                                <optgroup label="Dell N3000 Series">
                                    <option value="Dell N3024" ${switchData.model === 'Dell N3024' ? 'selected' : ''}>Dell N3024</option>
                                    <option value="Dell N3024P" ${switchData.model === 'Dell N3024P' ? 'selected' : ''}>Dell N3024P</option>
                                    <option value="Dell N3024F" ${switchData.model === 'Dell N3024F' ? 'selected' : ''}>Dell N3024F</option>
                                    <option value="Dell N3048" ${switchData.model === 'Dell N3048' ? 'selected' : ''}>Dell N3048</option>
                                    <option value="Dell N3048P" ${switchData.model === 'Dell N3048P' ? 'selected' : ''}>Dell N3048P</option>
                                </optgroup>
                                <optgroup label="Dell N3200 Series">
                                    <option value="Dell N3248" ${switchData.model === 'Dell N3248' ? 'selected' : ''}>Dell N3248</option>
                                    <option value="Dell N3224P" ${switchData.model === 'Dell N3224P' ? 'selected' : ''}>Dell N3224P</option>
                                    <option value="Dell N3224PXE" ${switchData.model === 'Dell N3224PXE' ? 'selected' : ''}>Dell N3224PXE</option>
                                    <option value="Dell N3248P" ${switchData.model === 'Dell N3248P' ? 'selected' : ''}>Dell N3248P</option>
                                    <option value="Dell N3248PXE" ${switchData.model === 'Dell N3248PXE' ? 'selected' : ''}>Dell N3248PXE</option>
                                </optgroup>
                                <optgroup label="Dell N4000 Series">
                                    <option value="Dell N4032" ${switchData.model === 'Dell N4032' ? 'selected' : ''}>Dell N4032</option>
                                    <option value="Dell N4032F" ${switchData.model === 'Dell N4032F' ? 'selected' : ''}>Dell N4032F</option>
                                    <option value="Dell N4064" ${switchData.model === 'Dell N4064' ? 'selected' : ''}>Dell N4064</option>
                                    <option value="Dell N4064F" ${switchData.model === 'Dell N4064F' ? 'selected' : ''}>Dell N4064F</option>
                                </optgroup>
                                <optgroup label="Dell S3000 Series">
                                    <option value="Dell S3048-ON" ${switchData.model === 'Dell S3048-ON' ? 'selected' : ''}>Dell S3048-ON</option>
                                    <option value="Dell S3124P" ${switchData.model === 'Dell S3124P' ? 'selected' : ''}>Dell S3124P</option>
                                    <option value="Dell S3124F" ${switchData.model === 'Dell S3124F' ? 'selected' : ''}>Dell S3124F</option>
                                </optgroup>
                                <optgroup label="Dell S4000 Series">
                                    <option value="Dell S4048-ON" ${switchData.model === 'Dell S4048-ON' ? 'selected' : ''}>Dell S4048-ON</option>
                                    <option value="Dell S4048T-ON" ${switchData.model === 'Dell S4048T-ON' ? 'selected' : ''}>Dell S4048T-ON</option>
                                    <option value="Dell S4112F-ON" ${switchData.model === 'Dell S4112F-ON' ? 'selected' : ''}>Dell S4112F-ON</option>
                                    <option value="Dell S4112T-ON" ${switchData.model === 'Dell S4112T-ON' ? 'selected' : ''}>Dell S4112T-ON</option>
                                    <option value="Dell S4128F-ON" ${switchData.model === 'Dell S4128F-ON' ? 'selected' : ''}>Dell S4128F-ON</option>
                                    <option value="Dell S4128T-ON" ${switchData.model === 'Dell S4128T-ON' ? 'selected' : ''}>Dell S4128T-ON</option>
                                </optgroup>
                                <optgroup label="Dell S5000 Series">
                                    <option value="Dell S5212F-ON" ${switchData.model === 'Dell S5212F-ON' ? 'selected' : ''}>Dell S5212F-ON</option>
                                    <option value="Dell S5224F-ON" ${switchData.model === 'Dell S5224F-ON' ? 'selected' : ''}>Dell S5224F-ON</option>
                                    <option value="Dell S5232F-ON" ${switchData.model === 'Dell S5232F-ON' ? 'selected' : ''}>Dell S5232F-ON</option>
                                    <option value="Dell S5248F-ON" ${switchData.model === 'Dell S5248F-ON' ? 'selected' : ''}>Dell S5248F-ON</option>
                                    <option value="Dell S5296F-ON" ${switchData.model === 'Dell S5296F-ON' ? 'selected' : ''}>Dell S5296F-ON</option>
                                </optgroup>
                                <optgroup label="Other Models">
                                    <option value="Custom Model" ${switchData.model === 'Custom Model' ? 'selected' : ''}>Custom Model (specify in description)</option>
                                </optgroup>
                            </select>
                        </div>
                    <div class="form-group">
                        <label for="edit-switch-description">Description</label>
                        <input type="text" id="edit-switch-description" value="${switchData.description || ''}" maxlength="100" 
                               pattern="[A-Za-z0-9 ._-]*" 
                               title="Only letters, numbers, spaces, periods, underscores, and hyphens allowed. No special characters.">
                    </div>
                    <div class="checkbox-group">
                        <input type="checkbox" id="edit-switch-enabled" ${switchData.enabled ? 'checked' : ''}>
                        <label for="edit-switch-enabled">Switch is enabled</label>
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">💾 Update Switch</button>
                        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
                    </div>
                </form>
            `);
            
            document.getElementById('edit-switch-form').addEventListener('submit', handleEditSwitch);
        }
        
        function createModal(title, content) {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>${title}</h3>
                        <button class="modal-close" onclick="closeModal()">×</button>
                    </div>
                    <div class="modal-body">
                        ${content}
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            return modal;
        }
        
        // Make function globally available
        window.createModal = createModal;
        
        function closeModal() {
            const modal = document.querySelector('.modal-overlay');
            if (modal) {
                modal.remove();
            }
        }
        
        // Make function globally available
        window.closeModal = closeModal;
        
        // Generic add switch modal when no floor is pre-selected
        function showGenericAddSwitchModal() {
            showToast('Please select a floor first', 'error');
        }
        
        // Helper function to open add switch modal with pre-selected floor
        function openAddSwitchModalWithFloor(floorId, floorName, siteName) {
            const modal = createModal('Add Switch to Floor', `
                <form id="add-switch-to-floor-form">
                    <input type="hidden" id="new-switch-floor-id" value="${floorId}">
                    <div class="form-group">
                        <label for="new-switch-site-name">Site</label>
                        <input type="text" id="new-switch-site-name" value="${siteName}" readonly>
                    </div>
                    <div class="form-group">
                        <label for="new-switch-floor-name">Floor</label>
                        <input type="text" id="new-switch-floor-name" value="${floorName}" readonly>
                    </div>
                    <div class="form-group">
                        <label for="new-switch-name">Switch Name</label>
                        <input type="text" id="new-switch-name" required placeholder="e.g., SITE_NAME-F11-R1-VAS-01" maxlength="50" 
                               pattern="[A-Z0-9_]+-F[0-9]{1,2}-[A-Z0-9]{1,3}-(VAS|AS)-[0-9]{1,2}$" 
                               title="Format: SITE_NAME-FLOOR-RACK/CABINET-VAS/AS-NUMBER (e.g., SITE_NAME-F11-R1-VAS-01 or SITE_NAME-F33-C1-AS-01)">
                    </div>
                    <div class="form-group">
                        <label for="new-switch-ip">IP Address</label>
                        <input type="text" id="new-switch-ip" required placeholder="e.g., 10.50.0.10" 
                               pattern="^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$">
                    </div>
                    <div class="form-group">
                        <label for="new-switch-model">Model</label>
                        <select id="new-switch-model" required>
                            <option value="">Select switch model...</option>
                            <optgroup label="Dell N2000 Series">
                                <option value="Dell N2024">Dell N2024</option>
                                <option value="Dell N2048">Dell N2048</option>
                                <option value="Dell N2048P">Dell N2048P</option>
                            </optgroup>
                            <optgroup label="Dell N3000 Series">
                                <option value="Dell N3024">Dell N3024</option>
                                <option value="Dell N3024P">Dell N3024P</option>
                                <option value="Dell N3024F">Dell N3024F</option>
                                <option value="Dell N3048">Dell N3048</option>
                                <option value="Dell N3048P">Dell N3048P</option>
                            </optgroup>
                            <optgroup label="Dell N3200 Series">
                                <option value="Dell N3248">Dell N3248</option>
                                <option value="Dell N3224P">Dell N3224P</option>
                                <option value="Dell N3224PXE">Dell N3224PXE</option>
                                <option value="Dell N3248P">Dell N3248P</option>
                                <option value="Dell N3248PXE">Dell N3248PXE</option>
                            </optgroup>
                            <optgroup label="Other Models">
                                <option value="Custom Model">Custom Model (specify in description)</option>
                            </optgroup>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="new-switch-description">Description</label>
                        <input type="text" id="new-switch-description" placeholder="e.g., Floor 11 VAS Switch" maxlength="100" 
                               pattern="[A-Za-z0-9 ._-]*" 
                               title="Only letters, numbers, spaces, periods, underscores, and hyphens allowed. No special characters.">
                    </div>
                    <div class="checkbox-group">
                        <input type="checkbox" id="new-switch-enabled" checked>
                        <label for="new-switch-enabled">Switch is enabled</label>
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">💾 Add Switch</button>
                        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
                    </div>
                </form>
            `);
            
            document.getElementById('add-switch-to-floor-form').addEventListener('submit', handleAddSwitchToFloor);
        }
        
        // Handle add switch to floor form submission
        async function handleAddSwitchToFloor(e) {
            e.preventDefault();
            
            // Get floor ID from hidden input
            const floorId = document.getElementById('new-switch-floor-id').value;
            
            const data = {
                name: document.getElementById('new-switch-name').value,
                ip_address: document.getElementById('new-switch-ip').value,
                model: document.getElementById('new-switch-model').value,
                description: document.getElementById('new-switch-description').value,
                enabled: document.getElementById('new-switch-enabled').checked,
                floor_id: parseInt(floorId)
            };
            
            try {
                const response = await fetch('/api/switches', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (response.ok) {
                    showToast('Switch added successfully', 'success');
                    closeModal();
                    
                    // Refresh current floor switches if in detail view
                    if (typeof currentFloorData !== 'undefined' && currentFloorData) {
                        await loadFloorSwitches(currentFloorData.id);
                    }
                    
                    // Refresh main switches data if available
                    if (typeof loadSwitches === 'function') {
                        loadSwitches();
                    }
                    
                    // Refresh all switches data if available
                    if (typeof loadAllSwitches === 'function') {
                        await loadAllSwitches();
                    }
                    
                    // Refresh sidebar counts
                    if (typeof refreshSidebarCounts === 'function') {
                        await refreshSidebarCounts();
                    }
                } else {
                    showToast(result.error, 'error');
                }
            } catch (error) {
                console.error('Error adding switch:', error);
                showToast('Error adding switch', 'error');
            }
        }
        
        // Make functions globally available
        window.showGenericAddSwitchModal = showGenericAddSwitchModal;
        window.openAddSwitchModalWithFloor = openAddSwitchModalWithFloor;
        window.handleAddSwitchToFloor = handleAddSwitchToFloor;
        
        // Function to refresh switch counts in sidebar
        async function refreshSidebarCounts() {
            try {
                // Reload all switches data to get updated counts
                await loadAllSwitches();
                
                // Reload sites data to refresh the sidebar
                await loadSites();
                
                console.log('Sidebar counts refreshed successfully');
            } catch (error) {
                console.error('Error refreshing sidebar counts:', error);
            }
        }
        
        // Make function globally available
        window.refreshSidebarCounts = refreshSidebarCounts;
        
        // Form handlers
        async function handleAddSite(e) {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());
            
            try {
                const response = await fetch('/api/sites', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (response.ok) {
                    showToast('Site created successfully', 'success');
                    closeModal();
                    loadSites(); // Refresh the site list
                } else {
                    showToast(result.error, 'error');
                }
            } catch (error) {
                showToast('Error creating site', 'error');
            }
        }
        
        async function handleAddFloor(e) {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());
            
            // Use the site ID from the hidden field in the form
            const siteId = document.getElementById('floor-site-id').value;
            if (!siteId) {
                showToast('Site ID is missing. Please select a site again.', 'error');
                return;
            }
            data.site_id = siteId;
            
            try {
                const response = await fetch('/api/floors', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (response.ok) {
                    showToast('Floor created successfully', 'success');
                    closeModal();
                    loadSites(); // Refresh the site list
                } else {
                    showToast(result.error, 'error');
                }
            } catch (error) {
                showToast('Error creating floor', 'error');
            }
        }
        
        async function handleEditSwitch(e) {
            e.preventDefault();
            const switchId = document.getElementById('edit-switch-id').value;
            const data = {
                name: document.getElementById('edit-switch-name').value,
                ip_address: document.getElementById('edit-switch-ip').value,
                model: document.getElementById('edit-switch-model').value,
                description: document.getElementById('edit-switch-description').value,
                enabled: document.getElementById('edit-switch-enabled').checked
            };
            
            try {
                const response = await fetch(`/api/switches/${switchId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (response.ok) {
                    showToast('Switch updated successfully', 'success');
                    closeModal();
                    // Refresh current floor if viewing
                    if (currentFloorData) {
                        await loadFloorSwitches(currentFloorData.id);
                    }
                } else {
                    showToast(result.error, 'error');
                }
            } catch (error) {
                showToast('Error updating switch', 'error');
            }
        }
        
        // Toast notification system
        function showToast(message, type) {
            const toast = document.createElement('div');
            toast.className = `toast ${type}`;
            toast.textContent = message;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.classList.add('show');
            }, 100);
            
            setTimeout(() => {
                toast.classList.remove('show');
                setTimeout(() => {
                    toast.remove();
                }, 300);
            }, 4000);
        }
        
        // Make function globally available
        window.showToast = showToast;
        
        // Site and Floor edit/delete action functions
        function editSite(siteId, siteName) {
            // Open edit site modal or form
            const modal = createModal('Edit Site', `
                <form id="edit-site-form">
                    <input type="hidden" id="edit-site-id" value="${siteId}">
                    <div class="form-group">
                        <label for="edit-site-name">Site Name</label>
                        <input type="text" id="edit-site-name" name="name" value="${siteName}" required placeholder="e.g., NYC_MAIN" maxlength="50">
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">💾 Update Site</button>
                        <button type="button" class="btn-danger" onclick="showDeleteSiteModal(${siteId}, '${siteName}')">🗑️ Delete Site</button>
                        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
                    </div>
                </form>
            `);
            
            document.getElementById('edit-site-form').addEventListener('submit', handleEditSite);
        }
        
        function showDeleteSiteModal(siteId, siteName) {
            const modal = createDeleteModal(
                'Delete Site',
                `Are you sure you want to delete the site <span class="delete-item-name">"${siteName}"</span>?`,
                'This will also delete all floors and switches in this site. This action cannot be undone.',
                () => deleteSite(siteId, siteName)
            );
        }
        
        
        function editFloor(floorId, floorName, siteId) {
            // Find the site name for the current site
            const site = sitesData.find(s => s.id == siteId);
            const siteName = site ? site.name : 'Unknown Site';
            
            const modal = createModal('Edit Floor', `
                <form id="edit-floor-form">
                    <input type="hidden" id="edit-floor-id" value="${floorId}">
                    <div class="form-group">
                        <label for="edit-floor-site-name">Site</label>
                        <input type="text" id="edit-floor-site-name" value="${siteName}" readonly>
                    </div>
                    <div class="form-group">
                        <label for="edit-floor-name">Floor Name</label>
                        <input type="text" id="edit-floor-name" name="name" value="${floorName}" required placeholder="e.g., Floor 1" maxlength="20" 
                               pattern="^(F[0-9]{1,2}|GF|PH|B[0-9]|Floor [0-9]{1,2}|[0-9]{1,2}|Ground Floor|Penthouse|Basement)$" 
                               title="Valid formats: F1-F99, GF, PH, B1-B9, Floor 1-99, 1-99, Ground Floor, Penthouse, or Basement">
                    </div>
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">💾 Update Floor</button>
                        <button type="button" class="btn-danger" onclick="deleteFloorFromModal(${floorId}, '${floorName}')">🗑️ Delete Floor</button>
                        <button type="button" class="btn-secondary" onclick="closeModal()">Cancel</button>
                    </div>
                </form>
            `);
            
            document.getElementById('edit-floor-form').addEventListener('submit', handleEditFloor);
        }
        
        function showDeleteSiteModal(siteId, siteName) {
            const modal = createDeleteModal(
                'Delete Site',
                `Are you sure you want to delete the site <span class="delete-item-name">"${siteName}"</span>?`,
                'This will also delete all floors and switches in this site. This action cannot be undone.',
                () => deleteSiteConfirmed(siteId, siteName)
            );
        }
        
        function deleteSiteConfirmed(siteId, siteName) {
            closeModal(); // Close the confirmation modal first
            
            fetch(`/api/sites/${siteId}`, { method: 'DELETE' })
                .then(response => response.json())
                .then(result => {
                    if (result.error) {
                        showToast(result.error, 'error');
                    } else {
                        showToast(result.message, 'success');
                        loadSites(); // Refresh the site list
                        // Clear results and reset UI
                        document.getElementById('switches-content').innerHTML = `
                            <div class="empty-state">
                                <div class="empty-icon">🔍</div>
                                <div class="empty-title">No Floor Selected</div>
                                <div class="empty-description">Choose a site and floor from the sidebar to view switch inventory</div>
                            </div>
                        `;
                        document.getElementById('switches-controls').style.display = 'none';
                        document.getElementById('stats-grid').style.display = 'none';
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showToast('Error deleting site', 'error');
                });
        }
        
        function deleteFloorFromModal(floorId, floorName) {
            // This function is called from within the edit floor modal
            closeModal(); // Close the edit modal first
            
            // Show confirmation modal
            const modal = createDeleteModal(
                'Delete Floor',
                `Are you sure you want to delete the floor <span class="delete-item-name">"${floorName}"</span>?`,
                'This will also delete all switches on this floor. This action cannot be undone.',
                () => {
                    closeModal(); // Close the confirmation modal
                    
                    fetch(`/api/floors/${floorId}`, { method: 'DELETE' })
                        .then(response => response.json())
                        .then(result => {
                            if (result.error) {
                                showToast(result.error, 'error');
                            } else {
                                showToast(result.message, 'success');
                                loadSites(); // Refresh the site list
                                // Clear current floor selection if it was the deleted floor
                                if (currentFloorData && currentFloorData.id == floorId) {
                                    currentFloorData = null;
                                    document.getElementById('switches-content').innerHTML = `
                                        <div class="empty-state">
                                            <div class="empty-icon">🔍</div>
                                            <div class="empty-title">No Floor Selected</div>
                                            <div class="empty-description">Choose a site and floor from the sidebar to view switch inventory</div>
                                        </div>
                                    `;
                                    document.getElementById('switches-controls').style.display = 'none';
                                    document.getElementById('stats-grid').style.display = 'none';
                                }
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            showToast('Error deleting floor', 'error');
                        });
                }
            );
        }
        
        
        function showDeleteSwitchModal(switchId, switchData) {
            const modal = createDeleteModal(
                'Delete Switch',
                `Are you sure you want to delete the switch <span class="delete-item-name">"${switchData.name}"</span>?`,
                'This action cannot be undone. The switch will be removed from the inventory.',
                () => {
                    closeModal();
                    fetch(`/api/switches/${switchId}`, { method: 'DELETE' })
                        .then(response => response.json())
                        .then(result => {
                            if (result.error) {
                                showToast(result.error, 'error');
                            } else {
                                showToast(result.message, 'success');
                                loadSwitches();
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            showToast('Error deleting switch', 'error');
                        });
                }
            );
        }
        
        // Form submission handlers for edit modals
        async function handleEditSite(e) {
            e.preventDefault();
            const siteId = document.getElementById('edit-site-id').value;
            const data = {
                name: document.getElementById('edit-site-name').value
            };
            
            try {
                const response = await fetch(`/api/sites/${siteId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (response.ok) {
                    showToast('Site updated successfully', 'success');
                    closeModal();
                    loadSites(); // Refresh the site list
                } else {
                    showToast(result.error, 'error');
                }
            } catch (error) {
                showToast('Error updating site', 'error');
            }
        }
        
        async function handleEditFloor(e) {
            e.preventDefault();
            const floorId = document.getElementById('edit-floor-id').value;
            const data = {
                name: document.getElementById('edit-floor-name').value
            };
            
            try {
                const response = await fetch(`/api/floors/${floorId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                if (response.ok) {
                    showToast('Floor updated successfully', 'success');
                    closeModal();
                    loadSites(); // Refresh the site list
                } else {
                    showToast(result.error, 'error');
                }
            } catch (error) {
                showToast('Error updating floor', 'error');
            }
        }
        
        // Create delete confirmation modal
        function createDeleteModal(title, message, warning, onConfirm) {
            const modal = document.createElement('div');
            modal.className = 'modal-overlay delete-modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h3><span>⚠️</span> ${title}</h3>
                        <button class="modal-close" onclick="closeModal()">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="delete-warning">
                            <div class="delete-warning-title">
                                <span>🚨</span> Warning
                            </div>
                            <div class="delete-warning-text">
                                ${message}
                            </div>
                            <div class="delete-warning-text">
                                ${warning}
                            </div>
                        </div>
                        <div class="delete-actions">
                            <button class="btn-cancel" onclick="closeModal()">Cancel</button>
                            <button class="btn-delete" id="confirm-delete-btn">🗑️ Delete</button>
                        </div>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            // Add event listener to delete button
            document.getElementById('confirm-delete-btn').addEventListener('click', onConfirm);
            
            return modal;
        }
        
        // Utility functions
        function showError(message) {
            document.getElementById('site-tree-container').innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">❌</div>
                    <div class="empty-title">Error</div>
                    <div class="empty-description">${message}</div>
                </div>
            `;
        }
    </script>
</body>
</html>
"""

LOGIN_TEMPLATE = r"""
<!DOCTYPE html>
<html>
<head>
    <title>Dell Switch Port Tracer</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='styles.css') }}">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        /* CSS Reset to prevent unwanted scrolling */
        * {
            box-sizing: border-box;
        }
        
        html, body {
            margin: 0;
            padding: 0;
            height: 100%;
            overflow-x: hidden; /* Prevent horizontal scroll */
        }
        
        .login-page {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            height: 100vh; /* Ensure exact viewport height */
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            position: relative; /* For absolute positioned elements */
        }
        .login-container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
            padding: 50px;
            width: 100%;
            max-width: 450px;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .logo-section {
            margin-bottom: 40px;
        }
        .logo-section img {
            height: 60px;
            margin-bottom: 20px;
            filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
        }
        .app-title {
            color: var(--deep-navy);
            font-size: 28px;
            font-weight: 700;
            margin: 0 0 12px 0;
            text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .app-subtitle {
            color: #6b7280;
            font-size: 16px;
            margin: 0 0 40px 0;
            font-weight: 500;
            opacity: 0.8;
        }
        .form-group {
            margin-bottom: 25px;
            text-align: left;
        }
        .form-group label {
            display: block;
            color: var(--deep-navy);
            font-weight: 600;
            margin-bottom: 10px;
            font-size: 15px;
        }
        .form-input {
            width: 100%;
            padding: 16px 20px;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            font-size: 16px;
            transition: all 0.3s ease;
            box-sizing: border-box;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(5px);
        }
        .form-input:focus {
            outline: none;
            border-color: var(--orange);
            box-shadow: 0 0 0 4px rgba(255, 152, 0, 0.1);
            background: white;
            transform: translateY(-2px);
        }
        .form-input::placeholder {
            color: #9ca3af;
            font-weight: 400;
        }
        .login-btn {
            width: 100%;
            background: linear-gradient(135deg, var(--orange), #e68900);
            color: white;
            border: none;
            padding: 18px 24px;
            border-radius: 12px;
            font-size: 17px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 8px 20px rgba(255, 152, 0, 0.3);
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 10px;
        }
        .login-btn:hover {
            background: linear-gradient(135deg, #e68900, #cc7700);
            transform: translateY(-3px);
            box-shadow: 0 12px 30px rgba(255, 152, 0, 0.4);
        }
        .login-btn:active {
            transform: translateY(-1px);
            box-shadow: 0 8px 20px rgba(255, 152, 0, 0.3);
        }
        .error-card {
            background: rgba(254, 242, 242, 0.95);
            border: 2px solid #fca5a5;
            border-radius: 12px;
            padding: 16px 20px;
            margin-top: 25px;
            color: #dc2626;
            font-size: 14px;
            text-align: left;
            backdrop-filter: blur(5px);
            box-shadow: 0 4px 12px rgba(220, 38, 38, 0.1);
        }
        .error-card strong {
            font-weight: 600;
            display: block;
            margin-bottom: 4px;
        }
        .feature-card {
            margin-top: 30px;
            padding: 20px;
            background: rgba(240, 249, 255, 0.8);
            border: 1px solid rgba(186, 230, 253, 0.5);
            border-radius: 12px;
            backdrop-filter: blur(5px);
        }
        .feature-note {
            color: #0369a1;
            font-size: 13px;
            line-height: 1.6;
            text-align: left;
        }
        .feature-note strong {
            color: var(--deep-navy);
            font-weight: 600;
        }
        .version-badge {
            position: absolute;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.9);
            color: var(--deep-navy);
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            backdrop-filter: blur(5px);
            border: 1px solid rgba(255, 255, 255, 0.3);
        }
        @media (max-width: 480px) {
            .login-container {
                padding: 40px 30px;
                margin: 0 20px;
                max-width: 400px;
            }
            .app-title {
                font-size: 24px;
            }
            .app-subtitle {
                font-size: 14px;
            }
            .version-badge {
                position: relative;
                top: auto;
                right: auto;
                margin-bottom: 20px;
                display: inline-block;
            }
        }
    </style>
</head>
<body class="login-page">
    <div class="version-badge">v2.1.6</div>
    
    <div class="login-container">
        <div class="logo-section">
            <img src="{{ url_for('static', filename='img/kmc_logo.png') }}" alt="KMC Logo">
            <h1 class="app-title">Switch Port Tracer</h1>
            <p class="app-subtitle">Enterprise Network Management Portal</p>
        </div>
        
        <form method="post">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" class="form-input" placeholder="Enter your username" required autofocus>
            </div>
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" class="form-input" placeholder="Enter your password" required>
            </div>
            <button type="submit" class="login-btn">🔐 Sign In</button>
        </form>
        
        {% if error %}
        <div class="error-card">
            <strong>❌ Authentication Failed</strong>
            {{ error }}
        </div>
        {% endif %}
    </div>
</body>
</html>
"""

# MAIN_TEMPLATE was moved to external file templates/main.html

@app.before_request
def before_request():
    session.permanent = True
    session.modified = True
    if 'username' in session:
        if 'last_activity' in session:
            last_activity = session['last_activity']
            if (datetime.now(timezone.utc) - last_activity).total_seconds() > app.config['PERMANENT_SESSION_LIFETIME'].total_seconds():
                session.clear()
                return redirect(url_for('login'))
        session['last_activity'] = datetime.now(timezone.utc)

@app.before_request
def check_cpu_before_request():
    """Monitor CPU load before processing compute-intensive requests.
    
    This function acts as a gatekeeper for resource-intensive operations like MAC tracing.
    It checks system CPU load and rejects requests if the system is under high load to
    prevent system overload and maintain service stability.
    
    CPU Load Monitoring:
    - Green Zone (0-40%): All requests accepted
    - Yellow Zone (40-60%): Limited concurrent requests
    - Red Zone (60%+): New requests rejected with 503 status
    
    Only applies to compute-intensive endpoints like '/trace' to avoid impacting
    regular web interface navigation and administrative functions.
    
    Returns:
        None: Allows request to proceed
        Response: 503 Service Unavailable if CPU load is too high
    """
    # Only check CPU for compute-intensive operations to avoid blocking UI navigation
    if request.endpoint in ['trace']:
        # Check if system can accept new requests based on current CPU load
        can_accept, reason = cpu_monitor.can_accept_request()
        if not can_accept:
            # Log CPU-based request rejection for monitoring and troubleshooting
            logger.warning(f"Request rejected due to high CPU load: {reason}")
            audit_logger.warning(f"CPU Protection - Request rejected from {request.remote_addr}: {reason}")
            return jsonify({
                'status': 'error', 
                'message': f'System under high load: {reason}. Please try again in a moment.',
                'error_type': 'cpu_overload'
            }), 503  # Service Unavailable

# Routes
@app.route('/cpu-status')
def cpu_status():
    """CPU monitoring status endpoint for admin users."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        stats = cpu_monitor.get_statistics()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/switch-protection-status')
def switch_protection_status():
    """Switch protection monitoring status endpoint for admin users."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    if not switch_monitor or not SWITCH_PROTECTION_AVAILABLE:
        return jsonify({'error': 'Switch protection monitoring not available'}), 503
    
    try:
        global_stats = switch_monitor.get_global_stats()
        return jsonify({
            'status': 'active',
            'timestamp': datetime.now().isoformat(),
            'global_stats': global_stats,
            'configuration': {
                'max_connections_per_switch': switch_monitor.max_connections_per_switch,
                'max_total_connections': switch_monitor.max_total_connections,
                'commands_per_second_limit': switch_monitor.commands_per_second_limit
            }
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_info = verify_user(username, password)
        if user_info:
            # Use display name or actual username for session
            display_name = user_info.get('display_name', username)
            session_username = user_info.get('username', username)
            
            session['username'] = session_username
            session['role'] = user_info['role']
            session['display_name'] = display_name
            session['auth_method'] = user_info.get('auth_method', 'local')
            
            auth_method = user_info.get('auth_method', 'local')
            audit_logger.info(f"User: {session_username} ({user_info['role']}) - LOGIN SUCCESS via {auth_method}")
            return redirect(url_for('index'))
        else:
            audit_logger.warning(f"User: {username} - LOGIN FAILED")
            return render_template_string(LOGIN_TEMPLATE, error="Invalid credentials")
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    username = session.get('username', 'Unknown')
    session.pop('username', None)
    audit_logger.info(f"User: {username} - LOGOUT")
    return redirect(url_for('login'))

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get switches data (role-based filtering handled in frontend)
    user_role = session.get('role', 'oss')
    formatted_data = format_switches_for_frontend()
    return render_template('main.html', 
                         username=session['username'],
                         user_role=user_role,
                         sites=formatted_data.get('sites', []),
                         sites_json=json.dumps(formatted_data))

@app.route('/health')
def health_check():
    """Health check endpoint for Kubernetes liveness and readiness probes."""
    try:
        # Use PostgreSQL to check if switches configuration is available
        site_count = Site.query.count()
        if site_count == 0:
            return jsonify({'status': 'unhealthy', 'reason': 'No sites configured'}), 503
        
        return jsonify({
            'status': 'healthy',
            'version': '2.1.5',
            'timestamp': datetime.now().isoformat(),
            'sites_count': site_count,
            'windows_auth': WINDOWS_AUTH_AVAILABLE
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'reason': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

# Utility functions (is_valid_mac, get_mac_format_error_message) moved to utils.py module

@app.route('/trace', methods=['POST'])
def trace():
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    site = data.get('site')
    floor = data.get('floor')
    mac = data.get('mac')
    username = session['username']
    
    if not all([site, floor, mac]):
        return jsonify({'error': 'Missing required fields'}), 400

    # MAC address validation to prevent command injection
    if not is_valid_mac(mac):
        audit_logger.warning(f"User: {username} - INVALID MAC FORMAT - MAC: {mac}")
        detailed_error = get_mac_format_error_message(mac)
        return jsonify(detailed_error), 400
    
    # Log the trace request
    audit_logger.info(f"User: {username} - TRACE REQUEST - Site: {site}, Floor: {floor}, MAC: {mac}")
    
    # Get switches for the specified site and floor
    switches = get_site_floor_switches(site, floor)
    
    if not switches:
        audit_logger.warning(f"User: {username} - NO SWITCHES FOUND - Site: {site}, Floor: {floor}")
        return jsonify({'error': 'No switches found for specified site and floor'}), 404
    
    # Trace MAC address
    results = trace_mac_on_switches(switches, mac, username)
    
    # Apply role-based filtering
    user_role = session.get('role', 'oss')
    filtered_results = apply_role_based_filtering(results, user_role)
    
    # Sort results to prioritize interface ports (Gi) over uplink ports (Te/Tw)
    def get_port_priority(result):
        if result['status'] != 'found':
            return 999  # Put non-found results at the end
        
        port_name = result.get('port', '')
        # Priority: Gi ports (access/interface) first, then Te/Tw (uplink) ports
        if port_name.startswith('Gi'):
            return 1  # Highest priority for Gigabit Ethernet (interface ports)
        elif port_name.startswith('Te'):
            return 2  # Lower priority for TenGig (uplink ports)
        elif port_name.startswith('Tw'):
            return 3  # Lowest priority for TwentyGig (uplink ports)
        else:
            return 4  # Other port types
    
    sorted_results = sorted(filtered_results, key=get_port_priority)
    
    return jsonify(sorted_results)

# CRUD Routes for Switch Management (NetAdmin/SuperAdmin only)

@app.route('/inventory')
def switch_inventory():
    """Hierarchical switch inventory interface for network administrators."""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    return render_template('inventory.html', username=session['username'], user_role=user_role)

@app.route('/api/switches')
def api_get_switches():
    """API endpoint to get all switches with their sites and floors."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        switches = db.session.query(Switch, Floor, Site).join(Floor, Switch.floor_id == Floor.id).join(Site, Floor.site_id == Site.id).all()
        
        switches_data = []
        for switch, floor, site in switches:
            switches_data.append({
                'id': switch.id,
                'name': switch.name,
                'ip_address': switch.ip_address,
                'model': switch.model,
                'description': switch.description or '',
                'enabled': switch.enabled,
                'site_name': site.name,
                'floor_name': floor.name,
                'site_id': site.id,
                'floor_id': floor.id
            })
        
        return jsonify(switches_data)
    except Exception as e:
        logger.error(f"Error fetching switches: {str(e)}")
        return jsonify({'error': 'Failed to fetch switches'}), 500

@app.route('/api/sites')
def api_get_sites():
    """API endpoint to get all sites and their floors."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        sites = Site.query.all()
        sites_data = []
        
        for site in sites:
            floors_data = []
            for floor in site.floors:
                floors_data.append({
                    'id': floor.id,
                    'name': floor.name
                })
            
            sites_data.append({
                'id': site.id,
                'name': site.name,
                'floors': floors_data
            })
        
        return jsonify(sites_data)
    except Exception as e:
        logger.error(f"Error fetching sites: {str(e)}")
        return jsonify({'error': 'Failed to fetch sites'}), 500

@app.route('/api/sites', methods=['POST'])
def api_create_site():
    """API endpoint to create a new site."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        data = request.json
        username = session['username']
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Missing required field: name'}), 400
        
        # Check if site name already exists
        existing_site = Site.query.filter(Site.name == data['name']).first()
        if existing_site:
            return jsonify({'error': 'Site name already exists'}), 400
        
        # Create new site
        new_site = Site(name=data['name'])
        db.session.add(new_site)
        db.session.commit()
        
        # Log the action
        audit_logger.info(f"User: {username} - SITE CREATED - {data['name']}")
        
        return jsonify({'message': 'Site created successfully', 'id': new_site.id}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating site: {str(e)}")
        return jsonify({'error': 'Failed to create site'}), 500

@app.route('/api/sites/<int:site_id>', methods=['PUT'])
def api_update_site(site_id):
    """API endpoint to update an existing site."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        site = Site.query.get_or_404(site_id)
        data = request.json
        username = session['username']
        
        # Store old value for audit log
        old_name = site.name
        
        # Check if new name conflicts with other sites
        if data.get('name') and data['name'] != site.name:
            existing = Site.query.filter(Site.name == data['name'], Site.id != site_id).first()
            if existing:
                return jsonify({'error': 'Site name already exists'}), 400
        
        # Update site fields
        if 'name' in data:
            site.name = data['name']
        
        db.session.commit()
        
        # Log the action
        audit_logger.info(f"User: {username} - SITE UPDATED - {old_name} -> {site.name}")
        
        return jsonify({'message': 'Site updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating site: {str(e)}")
        return jsonify({'error': 'Failed to update site'}), 500

@app.route('/api/sites/<int:site_id>', methods=['DELETE'])
def api_delete_site(site_id):
    """API endpoint to delete a site and all associated floors and switches."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        site = Site.query.get_or_404(site_id)
        username = session['username']
        
        # Store values for audit log
        site_name = site.name
        floor_count = len(site.floors)
        switch_count = sum(len(floor.switches) for floor in site.floors)
        
        # Delete site (cascading deletes will handle floors and switches)
        db.session.delete(site)
        db.session.commit()
        
        # Log the action
        audit_logger.info(f"User: {username} - SITE DELETED - {site_name} (with {floor_count} floors and {switch_count} switches)")
        
        return jsonify({'message': 'Site deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting site: {str(e)}")
        return jsonify({'error': 'Failed to delete site'}), 500

@app.route('/api/floors', methods=['POST'])
def api_create_floor():
    """API endpoint to create a new floor."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        data = request.json
        username = session['username']
        
        # Validate required fields
        required_fields = ['name', 'site_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if site exists
        site = Site.query.get(data['site_id'])
        if not site:
            return jsonify({'error': 'Site not found'}), 404
        
        # Check if floor name already exists in this site
        existing_floor = Floor.query.filter(
            Floor.name == data['name'], 
            Floor.site_id == data['site_id']
        ).first()
        if existing_floor:
            return jsonify({'error': 'Floor name already exists in this site'}), 400
        
        # Create new floor
        new_floor = Floor(
            name=data['name'],
            site_id=data['site_id']
        )
        db.session.add(new_floor)
        db.session.commit()
        
        # Log the action
        audit_logger.info(f"User: {username} - FLOOR CREATED - {data['name']} in site {site.name}")
        
        return jsonify({'message': 'Floor created successfully', 'id': new_floor.id}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating floor: {str(e)}")
        return jsonify({'error': 'Failed to create floor'}), 500

@app.route('/api/floors/<int:floor_id>', methods=['PUT'])
def api_update_floor(floor_id):
    """API endpoint to update an existing floor."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        floor = Floor.query.get_or_404(floor_id)
        data = request.json
        username = session['username']
        
        # Store old values for audit log
        old_name = floor.name
        old_site_name = floor.site.name
        
        # Check if new name conflicts with other floors in the same site
        if data.get('name') and data['name'] != floor.name:
            site_id = data.get('site_id', floor.site_id)
            existing = Floor.query.filter(
                Floor.name == data['name'], 
                Floor.site_id == site_id,
                Floor.id != floor_id
            ).first()
            if existing:
                return jsonify({'error': 'Floor name already exists in this site'}), 400
        
        # Update floor fields
        if 'name' in data:
            floor.name = data['name']
        if 'site_id' in data:
            # Verify new site exists
            new_site = Site.query.get(data['site_id'])
            if not new_site:
                return jsonify({'error': 'New site not found'}), 404
            floor.site_id = data['site_id']
        
        db.session.commit()
        
        # Log the action
        new_site_name = floor.site.name
        audit_logger.info(f"User: {username} - FLOOR UPDATED - {old_name} in {old_site_name} -> {floor.name} in {new_site_name}")
        
        return jsonify({'message': 'Floor updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating floor: {str(e)}")
        return jsonify({'error': 'Failed to update floor'}), 500

@app.route('/api/floors/<int:floor_id>', methods=['DELETE'])
def api_delete_floor(floor_id):
    """API endpoint to delete a floor and all associated switches."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        floor = Floor.query.get_or_404(floor_id)
        username = session['username']
        
        # Store values for audit log
        floor_name = floor.name
        site_name = floor.site.name
        switch_count = len(floor.switches)
        
        # Delete floor (cascading deletes will handle switches)
        db.session.delete(floor)
        db.session.commit()
        
        # Log the action
        audit_logger.info(f"User: {username} - FLOOR DELETED - {floor_name} in site {site_name} (with {switch_count} switches)")
        
        return jsonify({'message': 'Floor deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting floor: {str(e)}")
        return jsonify({'error': 'Failed to delete floor'}), 500

@app.route('/api/switches', methods=['POST'])
def api_create_switch():
    """API endpoint to create a new switch."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        data = request.json
        username = session['username']
        
        # Validate required fields
        required_fields = ['name', 'ip_address', 'model', 'floor_id']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Check if switch name or IP already exists
        existing_switch = Switch.query.filter(
            (Switch.name == data['name']) | (Switch.ip_address == data['ip_address'])
        ).first()
        
        if existing_switch:
            return jsonify({'error': 'Switch name or IP address already exists'}), 400
        
        # Create new switch
        new_switch = Switch(
            name=data['name'],
            ip_address=data['ip_address'],
            model=data['model'],
            description=data.get('description', ''),
            enabled=data.get('enabled', True),
            floor_id=data['floor_id']
        )
        
        db.session.add(new_switch)
        db.session.commit()
        
        # Log the action
        audit_logger.info(f"User: {username} - SWITCH CREATED - {data['name']} ({data['ip_address']})")
        
        return jsonify({'message': 'Switch created successfully', 'id': new_switch.id}), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating switch: {str(e)}")
        return jsonify({'error': 'Failed to create switch'}), 500

@app.route('/api/switches/<int:switch_id>', methods=['PUT'])
def api_update_switch(switch_id):
    """API endpoint to update an existing switch."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        switch = Switch.query.get_or_404(switch_id)
        data = request.json
        username = session['username']
        
        # Store old values for audit log
        old_name = switch.name
        old_ip = switch.ip_address
        
        # Check if new name or IP conflicts with other switches
        if data.get('name') and data['name'] != switch.name:
            existing = Switch.query.filter(Switch.name == data['name'], Switch.id != switch_id).first()
            if existing:
                return jsonify({'error': 'Switch name already exists'}), 400
        
        if data.get('ip_address') and data['ip_address'] != switch.ip_address:
            existing = Switch.query.filter(Switch.ip_address == data['ip_address'], Switch.id != switch_id).first()
            if existing:
                return jsonify({'error': 'IP address already exists'}), 400
        
        # Update switch fields
        if 'name' in data:
            switch.name = data['name']
        if 'ip_address' in data:
            switch.ip_address = data['ip_address']
        if 'model' in data:
            switch.model = data['model']
        if 'description' in data:
            switch.description = data['description']
        if 'enabled' in data:
            switch.enabled = data['enabled']
        if 'floor_id' in data:
            switch.floor_id = data['floor_id']
        
        db.session.commit()
        
        # Log the action
        audit_logger.info(f"User: {username} - SWITCH UPDATED - {old_name} ({old_ip}) -> {switch.name} ({switch.ip_address})")
        
        return jsonify({'message': 'Switch updated successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating switch: {str(e)}")
        return jsonify({'error': 'Failed to update switch'}), 500

@app.route('/api/switches/<int:switch_id>', methods=['DELETE'])
def api_delete_switch(switch_id):
    """API endpoint to delete a switch."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        switch = Switch.query.get_or_404(switch_id)
        username = session['username']
        
        # Store values for audit log
        switch_name = switch.name
        switch_ip = switch.ip_address
        
        db.session.delete(switch)
        db.session.commit()
        
        # Log the action
        audit_logger.info(f"User: {username} - SWITCH DELETED - {switch_name} ({switch_ip})")
        
        return jsonify({'message': 'Switch deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting switch: {str(e)}")
        return jsonify({'error': 'Failed to delete switch'}), 500

## VLAN Management API

@app.route('/api/switches/list', methods=['GET'])
def api_get_switches_list():
    """API endpoint to retrieve list of switches for dropdowns with site/floor info."""
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin', 'oss']:
        return jsonify({'error': 'Insufficient permissions'}), 403

    try:
        # Join with floors and sites to get complete information
        switches = db.session.query(Switch, Floor, Site).join(
            Floor, Switch.floor_id == Floor.id
        ).join(
            Site, Floor.site_id == Site.id
        ).filter(Switch.enabled == True).all()
        
        switches_list = []
        for switch, floor, site in switches:
            switches_list.append({
                'id': switch.id,
                'name': switch.name,
                'ip_address': switch.ip_address,
                'model': switch.model,
                'description': switch.description or '',
                'site_name': site.name,
                'floor_name': floor.name,
                'site_id': site.id,
                'floor_id': floor.id
            })
        return jsonify(switches_list)
    except Exception as e:
        logger.error(f"Failed to retrieve switches: {str(e)}")
        return jsonify({'error': 'Failed to retrieve switches'}), 500

# ================================================================
# ADVANCED VLAN MANAGEMENT API ENDPOINTS
# ================================================================
# 
# TROUBLESHOOTING GUIDE:
# - All VLAN operations require NetAdmin or SuperAdmin role
# - Check audit.log for security violations and failed attempts
# - Monitor port_tracer.log for switch connectivity issues
# - Verify SWITCH_USERNAME/SWITCH_PASSWORD env vars are set
# - Ensure Dell switches allow SSH connections (max 10 concurrent)
# - VLAN operations timeout after 60 seconds for safety
# 
# SUPPORTED ENDPOINTS:
# - POST /api/vlan/change - Main VLAN assignment workflow
# - POST /api/vlan/check  - Check VLAN existence on switch
# - POST /api/port/status - Get current port status and config
# ================================================================

@app.route('/vlan')
def vlan_management():
    """Advanced VLAN management interface."""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    return render_template('vlan.html', username=session['username'], user_role=user_role)

# Import and add advanced VLAN management routes
from app.core.vlan_manager import vlan_change_workflow, add_vlan_management_routes

@app.route('/api/vlan/change', methods=['POST'])
def api_change_port_vlan_advanced():
    """
    Advanced VLAN Change API Endpoint (v2.1.2)
    ==========================================
    
    Provides comprehensive VLAN management with enterprise-grade input validation,
    security checks, and detailed audit logging. This endpoint implements the
    enhanced VLAN Manager security features introduced in version 2.1.2.
    
    SECURITY FEATURES:
    - Multi-layer input validation to prevent command injection attacks
    - Enterprise-grade port format validation (Dell switch compatibility)
    - VLAN ID validation according to IEEE 802.1Q standards
    - VLAN name validation with business naming convention support
    - Port description sanitization to prevent CLI command injection
    - Comprehensive audit logging for security compliance
    
    VALIDATION DETAILS:
    - Port formats: Supports Dell interface naming (Gi, Te, Tw) with ranges
    - VLAN IDs: 1-4094 (IEEE standard), excludes reserved VLANs (0, 4095)
    - VLAN names: Enterprise naming conventions (Zone_Client_Name, etc.)
    - Descriptions: Safe characters only, max 200 chars, no injection patterns
    
    ACCESS CONTROL:
    - Requires authentication (session-based)
    - NetAdmin or SuperAdmin role required
    - All security violations logged for audit
    
    Returns:
        dict: VLAN change results or detailed validation error messages
    """
    # Authentication and authorization checks
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        data = request.json
        username = session['username']
        
        # Validate required fields are present
        required_fields = ['switch_id', 'ports', 'vlan_id']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Import enterprise-grade validation functions from VLAN Manager v2
        from app.core.vlan_manager import (is_valid_port_input, is_valid_port_description, 
                                        is_valid_vlan_id, is_valid_vlan_name,
                                        get_port_format_error_message, get_vlan_format_error_message)
        
        # SECURITY CHECKPOINT 1: Validate port input format
        # Prevents command injection through malformed port specifications
        ports_input = data.get('ports', '').strip()
        if not is_valid_port_input(ports_input):
            # Log security violation for audit trail
            audit_logger.warning(f"User: {username} - SECURITY VIOLATION - INVALID PORT FORMAT - Attempted: {ports_input}")
            detailed_error = get_port_format_error_message(ports_input)
            return jsonify(detailed_error), 400
        
        # SECURITY CHECKPOINT 2: Validate VLAN ID according to IEEE standards
        # Ensures VLAN ID is within valid range and prevents injection
        vlan_id = data.get('vlan_id')
        if not is_valid_vlan_id(vlan_id):
            # Log security violation for audit trail
            audit_logger.warning(f"User: {username} - SECURITY VIOLATION - INVALID VLAN ID - Attempted: {vlan_id}")
            detailed_error = get_vlan_format_error_message('vlan_id', str(vlan_id))
            return jsonify(detailed_error), 400
        
        # SECURITY CHECKPOINT 3: Validate VLAN name for business standards (optional if keeping existing)
        # Prevents command injection and enforces enterprise naming conventions
        vlan_name = data.get('vlan_name', '').strip()
        keep_existing_vlan_name = data.get('keep_existing_vlan_name', False)
        
        # Convert string 'true'/'false' to boolean if needed
        if isinstance(keep_existing_vlan_name, str):
            keep_existing_vlan_name = keep_existing_vlan_name.lower() == 'true'
        
        # Only validate VLAN name if not keeping existing name
        if not keep_existing_vlan_name and vlan_name and not is_valid_vlan_name(vlan_name):
            # Log security violation for audit trail
            audit_logger.warning(f"User: {username} - SECURITY VIOLATION - INVALID VLAN NAME - Attempted: {vlan_name}")
            detailed_error = get_vlan_format_error_message('vlan_name', vlan_name)
            return jsonify(detailed_error), 400
        
        # Check VLAN name requirement (only if not keeping existing name)
        if not keep_existing_vlan_name and not vlan_name:
            return jsonify({
                'error': 'VLAN name required',
                'details': 'VLAN name is required unless "Keep existing VLAN name" option is selected.'
            }), 400
        
        # SECURITY CHECKPOINT 4: Validate port description (optional but critical)
        # Sanitizes description to prevent CLI command injection attacks
        description = data.get('description', '').strip()
        if description and not is_valid_port_description(description):
            # Log security violation for audit trail
            audit_logger.warning(f"User: {username} - SECURITY VIOLATION - INVALID PORT DESCRIPTION - Attempted: {description}")
            detailed_error = get_vlan_format_error_message('description', description)
            return jsonify(detailed_error), 400
        
        # Process optional workflow control flags
        force_change = data.get('force_change', False)
        skip_non_access = data.get('skip_non_access', False)
        
        # Convert string 'true'/'false' to boolean if needed for workflow control flags
        if isinstance(force_change, str):
            force_change = force_change.lower() == 'true'
        if isinstance(skip_non_access, str):
            skip_non_access = skip_non_access.lower() == 'true'
        
        # Handle preview_only parameter
        preview_only = data.get('preview_only', False)
        if isinstance(preview_only, str):
            preview_only = preview_only.lower() == 'true'
        
        # Execute VLAN change workflow with validated and sanitized inputs
        # All inputs have passed security validation at this point
        result = vlan_change_workflow(
            switch_id=data['switch_id'],
            ports_input=ports_input,        # Validated port format
            description=description,         # Sanitized description
            vlan_id=vlan_id,                # Validated VLAN ID
            vlan_name=vlan_name,            # Validated VLAN name
            force_change=force_change,
            skip_non_access=skip_non_access,
            keep_existing_vlan_name=keep_existing_vlan_name,
            preview_only=preview_only       # Preview mode flag
        )
        
        # Comprehensive audit logging for security compliance
        if result['status'] == 'success':
            audit_logger.info(f"User: {username} - VLAN CHANGE SUCCESS - Switch: {result.get('switch_info', {}).get('name', 'unknown')}, VLAN: {vlan_id} ({vlan_name}), Ports: {ports_input}, Changed: {len(result.get('ports_changed', []))}")
        elif result['status'] == 'confirmation_needed':
            # Confirmation needed is not a failure - it's a normal workflow state
            confirmation_type = result.get('type', 'unknown')
            audit_logger.info(f"User: {username} - VLAN CHANGE CONFIRMATION NEEDED - Switch ID: {data['switch_id']}, VLAN: {vlan_id}, Type: {confirmation_type}")
        else:
            # Only log actual errors/failures
            audit_logger.warning(f"User: {username} - VLAN CHANGE FAILED - Switch ID: {data['switch_id']}, VLAN: {vlan_id}, Error: {result.get('error', result.get('status', 'unknown'))}")
        
        return jsonify(result)
        
    except Exception as e:
        # Log unexpected errors for debugging and security monitoring
        logger.error(f"VLAN change API unexpected error: {str(e)}")
        audit_logger.error(f"User: {session.get('username', 'unknown')} - VLAN CHANGE API ERROR: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/vlan/check', methods=['POST'])
def api_check_vlan():
    """
    VLAN Existence Check API Endpoint (v2.1.2)
    ==========================================
    
    Secure API endpoint for checking VLAN existence on Dell switches with
    comprehensive input validation and security features.
    
    SECURITY FEATURES:
    - IEEE 802.1Q VLAN ID validation (1-4094 range)
    - Command injection prevention through strict input validation
    - Comprehensive audit logging for security compliance
    - Authentication and role-based authorization
    
    FUNCTIONALITY:
    - Connects to specified switch via secure SSH
    - Queries VLAN table for existence verification
    - Returns VLAN details including name and configuration status
    - Supports multiple Dell switch models (N2000, N3000, N3200)
    
    SUPPORTED MODELS:
    - Dell N2048 (N2000 series) with specialized command handling
    - Dell N3000 series switches
    - Dell N3200 series switches (N3248)
    
    ACCESS CONTROL:
    - NetAdmin or SuperAdmin role required
    - Session-based authentication
    - All invalid attempts logged for security monitoring
    
    Returns:
        dict: VLAN information or detailed validation error messages
    """
    # Authentication and authorization validation
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        from app.core.vlan_manager import VLANManager, is_valid_vlan_id, get_vlan_format_error_message
        data = request.json
        username = session['username']
        switch_id = data.get('switch_id')
        vlan_id = data.get('vlan_id')
        
        # Validate required parameters
        if not all([switch_id, vlan_id]):
            return jsonify({'error': 'Missing switch_id or vlan_id'}), 400
        
        # SECURITY CHECKPOINT: Validate VLAN ID according to IEEE 802.1Q standards
        # Prevents command injection and ensures compliance with VLAN standards
        if not is_valid_vlan_id(vlan_id):
            # Log security violation with detailed information for audit
            audit_logger.warning(f"User: {username} - SECURITY VIOLATION - INVALID VLAN ID - Switch ID: {switch_id}, Attempted VLAN: {vlan_id}")
            detailed_error = get_vlan_format_error_message('vlan_id', str(vlan_id))
            return jsonify(detailed_error), 400
        
        # Database query to retrieve switch information
        switch = Switch.query.get(switch_id)
        if not switch:
            audit_logger.warning(f"User: {username} - VLAN CHECK FAILED - Switch not found: ID {switch_id}")
            return jsonify({'error': 'Switch not found'}), 404
        
        # Initialize secure VLAN manager connection
        vlan_manager = VLANManager(
            switch.ip_address,
            SWITCH_USERNAME,
            SWITCH_PASSWORD,
            switch.model
        )
        
        # Attempt secure SSH connection to switch
        if not vlan_manager.connect():
            audit_logger.error(f"User: {username} - VLAN CHECK CONNECTION FAILED - Switch: {switch.name} ({switch.ip_address})")
            return jsonify({'error': 'Could not connect to switch'}), 500
        
        try:
            # Execute VLAN existence check with model-specific command handling
            vlan_info = vlan_manager.get_vlan_info(vlan_id)
            
            # Log successful VLAN check for audit trail
            audit_logger.info(f"User: {username} - VLAN CHECK SUCCESS - Switch: {switch.name} ({switch.ip_address}), VLAN: {vlan_id}, Exists: {vlan_info.get('exists', False)}")
            
            return jsonify(vlan_info)
            
        finally:
            # Always ensure secure disconnection from switch
            vlan_manager.disconnect()
            
    except Exception as e:
        # Log unexpected errors for security monitoring and debugging
        logger.error(f"VLAN check API unexpected error: {str(e)}")
        audit_logger.error(f"User: {session.get('username', 'unknown')} - VLAN CHECK API ERROR - Switch ID: {switch_id}, VLAN: {vlan_id}, Error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/session/keepalive', methods=['POST'])
def api_session_keepalive():
    """
    Session Keep-Alive API Endpoint
    ===============================
    
    Allows authenticated users to extend their session before timeout.
    This endpoint resets the session's last activity timestamp, effectively
    extending the session for another full timeout period.
    
    Returns:
        dict: Success status or error message
    """
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Not authenticated'}), 401
    
    try:
        # Update the session's last activity timestamp
        session['last_activity'] = datetime.now(timezone.utc)
        session.permanent = True
        session.modified = True
        
        username = session['username']
        audit_logger.info(f"User: {username} - SESSION EXTENDED - Keep-alive request")
        
        return jsonify({
            'success': True, 
            'message': 'Session extended successfully',
            'timeout_minutes': int(app.config['PERMANENT_SESSION_LIFETIME'].total_seconds() / 60)
        })
        
    except Exception as e:
        logger.error(f"Session keep-alive error: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/session/check', methods=['POST'])
def api_session_check():
    """
    Session Validity Check API Endpoint
    ==================================
    
    Validates current session status and returns validity information.
    Used by frontend to detect stale sessions and ensure consistent
    session state management across browser tabs and navigation.
    
    This endpoint helps prevent users from operating with expired sessions
    by providing a way to check session validity without extending it.
    
    Returns:
        dict: Session validity status and information
    """
    try:
        # Check if user is authenticated
        if 'username' not in session:
            return jsonify({'valid': False, 'reason': 'No active session'}), 401
        
        # Check if session has expired based on last activity
        if 'last_activity' in session:
            last_activity = session['last_activity']
            time_elapsed = (datetime.now(timezone.utc) - last_activity).total_seconds()
            session_timeout = app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()
            
            if time_elapsed > session_timeout:
                # Session has expired, clear it
                session.clear()
                audit_logger.info(f"Session expired during validity check - Time elapsed: {time_elapsed}s")
                return jsonify({'valid': False, 'reason': 'Session expired'}), 401
        
        # Session is valid
        username = session['username']
        user_role = session.get('role', 'oss')
        time_remaining = app.config['PERMANENT_SESSION_LIFETIME'].total_seconds()
        
        if 'last_activity' in session:
            time_elapsed = (datetime.now(timezone.utc) - session['last_activity']).total_seconds()
            time_remaining = max(0, app.config['PERMANENT_SESSION_LIFETIME'].total_seconds() - time_elapsed)
        
        return jsonify({
            'valid': True,
            'username': username,
            'role': user_role,
            'time_remaining_minutes': int(time_remaining / 60),
            'session_timeout_minutes': int(app.config['PERMANENT_SESSION_LIFETIME'].total_seconds() / 60)
        })
        
    except Exception as e:
        logger.error(f"Session check error: {str(e)}")
        return jsonify({'valid': False, 'reason': 'Internal server error'}), 500

@app.route('/api/port/status', methods=['POST'])
def api_check_port_status():
    """
    Port Status Check API Endpoint (v2.1.2)
    =======================================
    
    Secure API endpoint for retrieving detailed port status information from
    Dell switches with comprehensive input validation and security features.
    
    SECURITY FEATURES:
    - Enterprise-grade port format validation (Dell switch compatibility)
    - Command injection prevention through strict input validation
    - Comprehensive audit logging for security compliance
    - Authentication and role-based authorization
    
    FUNCTIONALITY:
    - Connects to specified switch via secure SSH
    - Retrieves port operational status (up/down)
    - Queries port mode configuration (access/trunk/general)
    - Returns VLAN assignments and descriptions
    - Identifies uplink ports based on model and description
    
    PORT INFORMATION RETURNED:
    - Operational status (up/down/unknown)
    - Port mode (access/trunk/general)
    - Current VLAN assignment
    - Port description (if configured)
    - Uplink detection flag
    - Raw configuration output for debugging
    
    SUPPORTED MODELS:
    - Dell N2048 (N2000 series) with specialized command handling
    - Dell N3000 series switches
    - Dell N3200 series switches (N3248)
    
    ACCESS CONTROL:
    - NetAdmin or SuperAdmin role required
    - Session-based authentication
    - All invalid attempts logged for security monitoring
    
    Returns:
        dict: Port status information or detailed validation error messages
    """
    # Authentication and authorization validation
    if 'username' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user_role = session.get('role', 'oss')
    if user_role not in ['netadmin', 'superadmin']:
        return jsonify({'error': 'Insufficient permissions'}), 403
    
    try:
        from app.core.vlan_manager import VLANManager, is_valid_port_input, get_port_format_error_message
        data = request.json
        username = session['username']
        switch_id = data.get('switch_id')
        ports_input = data.get('ports', '').strip()
        
        # Validate required parameters
        if not all([switch_id, ports_input]):
            return jsonify({'error': 'Missing switch_id or ports'}), 400
        
        # SECURITY CHECKPOINT: Validate port input format
        # Prevents command injection through malformed port specifications
        if not is_valid_port_input(ports_input):
            # Log security violation with detailed information for audit
            audit_logger.warning(f"User: {username} - SECURITY VIOLATION - INVALID PORT FORMAT - Switch ID: {switch_id}, Attempted Ports: {ports_input}")
            detailed_error = get_port_format_error_message(ports_input)
            return jsonify(detailed_error), 400
        
        # Database query to retrieve switch information
        switch = Switch.query.get(switch_id)
        if not switch:
            audit_logger.warning(f"User: {username} - PORT STATUS CHECK FAILED - Switch not found: ID {switch_id}")
            return jsonify({'error': 'Switch not found'}), 404
        
        # Initialize secure VLAN manager connection
        vlan_manager = VLANManager(
            switch.ip_address,
            SWITCH_USERNAME,
            SWITCH_PASSWORD,
            switch.model
        )
        
        # Attempt secure SSH connection to switch
        if not vlan_manager.connect():
            audit_logger.error(f"User: {username} - PORT STATUS CONNECTION FAILED - Switch: {switch.name} ({switch.ip_address})")
            return jsonify({'error': 'Could not connect to switch'}), 500
        
        try:
            # Parse and validate port specifications
            ports = vlan_manager.parse_port_range(ports_input)
            port_statuses = []
            
            # Query each port for detailed status information
            for port in ports:
                # Get comprehensive port status including mode, VLAN, and description
                status = vlan_manager.get_port_status(port)
                
                # Add uplink detection based on switch model and port characteristics
                status['is_uplink'] = vlan_manager.is_uplink_port(port)
                
                port_statuses.append(status)
            
            # Log successful port status check for audit trail
            audit_logger.info(f"User: {username} - PORT STATUS SUCCESS - Switch: {switch.name} ({switch.ip_address}), Ports: {ports_input}, Count: {len(port_statuses)}")
            
            return jsonify({
                'ports': port_statuses,
                'switch_model': switch.model,
                'switch_name': switch.name,
                'switch_ip': switch.ip_address
            })
            
        finally:
            # Always ensure secure disconnection from switch
            vlan_manager.disconnect()
            
    except Exception as e:
        # Log unexpected errors for security monitoring and debugging
        logger.error(f"Port status API unexpected error: {str(e)}")
        audit_logger.error(f"User: {session.get('username', 'unknown')} - PORT STATUS API ERROR - Switch ID: {switch_id}, Ports: {ports_input}, Error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    print("🔌 Starting Dell Switch Port Tracer Web Service...")
    print(f"📊 Web Interface: http://localhost:5000")
    print("👤 Available Users:")
    print("   • OSS: oss / oss123 (Limited access)")
    print("   • NetAdmin: netadmin / netadmin123 (Full access)")
    print("   • SuperAdmin: superadmin / superadmin123 (Full access)")
    print("   • Legacy: admin / password (Full access)") 
    print("📝 Logs: port_tracer.log (system) | audit.log (user actions)")
    print("🔒 Features: Role-based VLAN filtering, Dell uplink detection")
    
    # Production configuration
    app.run(debug=False, host='0.0.0.0', port=5000)
