
import json
from port_tracer_web import app, db
from database import Site, Floor, Switch

def migrate_switches():
    with app.app_context():
        db.create_all()

        with open('switches.json', 'r') as f:
            data = json.load(f)

        for site_name, site_data in data['sites'].items():
            new_site = Site(name=site_name)
            db.session.add(new_site)
            db.session.commit()

            for floor_name, floor_data in site_data['floors'].items():
                new_floor = Floor(name=floor_name, site_id=new_site.id)
                db.session.add(new_floor)
                db.session.commit()

                for switch_name, switch_data in floor_data['switches'].items():
                    new_switch = Switch(
                        name=switch_name,
                        ip_address=switch_data['ip_address'],
                        model=switch_data['model'],
                        description=switch_data.get('description', ''),
                        enabled=switch_data.get('enabled', True),
                        floor_id=new_floor.id
                    )
                    db.session.add(new_switch)
        db.session.commit()

if __name__ == '__main__':
    migrate_switches()
    print("Switch data migrated successfully!")

