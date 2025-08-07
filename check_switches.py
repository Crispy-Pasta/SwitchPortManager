#!/usr/bin/env python3
from port_tracer_web import app, db, Switch, Floor, Site

with app.app_context():
    # First check for PBCOM switches
    switches = db.session.query(Switch, Floor, Site).join(Floor, Switch.floor_id == Floor.id).join(Site, Floor.site_id == Site.id).filter(Switch.name.like("%PBCOM%")).all()
    if switches:
        print("PBCOM switches found:")
        for switch, floor, site in switches:
            print(f"  {switch.name} - {switch.ip_address} - Model: {switch.model} - Site: {site.name} - Floor: {floor.name}")
    else:
        print("No PBCOM switches found.")
        
    # Check for switch with IP 10.65.0.11
    print("\nSearching for switch with IP 10.65.0.11...")
    switches = db.session.query(Switch, Floor, Site).join(Floor, Switch.floor_id == Floor.id).join(Site, Floor.site_id == Site.id).filter(Switch.ip_address == "10.65.0.11").all()
    if switches:
        print("Found switch with IP 10.65.0.11:")
        for switch, floor, site in switches:
            print(f"  {switch.name} - {switch.ip_address} - Model: {switch.model} - Site: {site.name} - Floor: {floor.name}")
    else:
        print("No switch found with IP 10.65.0.11")
        
    print("\nListing all switches in database:")
    all_switches = db.session.query(Switch, Floor, Site).join(Floor, Switch.floor_id == Floor.id).join(Site, Floor.site_id == Site.id).all()
    for switch, floor, site in all_switches:
        print(f"  {switch.name} - {switch.ip_address} - Model: {switch.model} - Site: {site.name} - Floor: {floor.name}")
