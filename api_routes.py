#!/usr/bin/env python3
"""
API Routes Module for Dell Switch Port Tracer
=============================================

This module contains all API routes for inventory management, including
CRUD operations for sites, floors, and switches.

Features:
- RESTful API endpoints for inventory management
- Role-based access control
- Comprehensive input validation
- Audit logging for all operations
- Error handling and status codes

Author: Network Operations Team
Version: 2.1.3
Last Updated: August 2025
"""

import logging
from flask import Blueprint, request, jsonify, session
from database import db, Site, Floor, Switch
from auth import require_role

# Configure logger
logger = logging.getLogger(__name__)

# Create blueprint for API routes
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Audit logging for API operations
audit_logger = logging.getLogger('audit')


@api_bp.route('/switches')
@require_role('netadmin', 'superadmin')
def get_switches():
    """API endpoint to get all switches with their sites and floors."""
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


@api_bp.route('/sites')
@require_role('netadmin', 'superadmin')
def get_sites():
    """API endpoint to get all sites and their floors."""
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


@api_bp.route('/sites', methods=['POST'])
@require_role('netadmin', 'superadmin')
def create_site():
    """API endpoint to create a new site."""
    try:
        data = request.json
        username = session.get('username', 'unknown')
        
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


@api_bp.route('/sites/<int:site_id>', methods=['PUT'])
@require_role('netadmin', 'superadmin')
def update_site(site_id):
    """API endpoint to update an existing site."""
    try:
        site = Site.query.get_or_404(site_id)
        data = request.json
        username = session.get('username', 'unknown')
        
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


@api_bp.route('/sites/<int:site_id>', methods=['DELETE'])
@require_role('netadmin', 'superadmin')
def delete_site(site_id):
    """API endpoint to delete a site and all associated floors and switches."""
    try:
        site = Site.query.get_or_404(site_id)
        username = session.get('username', 'unknown')
        
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


@api_bp.route('/floors', methods=['POST'])
@require_role('netadmin', 'superadmin')
def create_floor():
    """API endpoint to create a new floor."""
    try:
        data = request.json
        username = session.get('username', 'unknown')
        
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


@api_bp.route('/floors/<int:floor_id>', methods=['PUT'])
@require_role('netadmin', 'superadmin')
def update_floor(floor_id):
    """API endpoint to update an existing floor."""
    try:
        floor = Floor.query.get_or_404(floor_id)
        data = request.json
        username = session.get('username', 'unknown')
        
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


@api_bp.route('/floors/<int:floor_id>', methods=['DELETE'])
@require_role('netadmin', 'superadmin')
def delete_floor(floor_id):
    """API endpoint to delete a floor and all associated switches."""
    try:
        floor = Floor.query.get_or_404(floor_id)
        username = session.get('username', 'unknown')
        
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


@api_bp.route('/switches', methods=['POST'])
@require_role('netadmin', 'superadmin')
def create_switch():
    """API endpoint to create a new switch."""
    try:
        data = request.json
        username = session.get('username', 'unknown')
        
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


@api_bp.route('/switches/<int:switch_id>', methods=['PUT'])
@require_role('netadmin', 'superadmin')
def update_switch(switch_id):
    """API endpoint to update an existing switch."""
    try:
        switch = Switch.query.get_or_404(switch_id)
        data = request.json
        username = session.get('username', 'unknown')
        
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


@api_bp.route('/switches/<int:switch_id>', methods=['DELETE'])
@require_role('netadmin', 'superadmin')
def delete_switch(switch_id):
    """API endpoint to delete a switch."""
    try:
        switch = Switch.query.get_or_404(switch_id)
        username = session.get('username', 'unknown')
        
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


@api_bp.route('/switches/list', methods=['GET'])
@require_role('netadmin', 'superadmin', 'oss')
def get_switches_list():
    """API endpoint to retrieve list of switches for dropdowns with site/floor info."""
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
