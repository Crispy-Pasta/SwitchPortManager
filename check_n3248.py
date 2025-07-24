import json

# Load switches.json
with open('switches.json', 'r') as f:
    data = json.load(f)

# Find Dell N3248 switches
n3248_switches = []
sites = data.get('sites', {})
for site_name, site_data in sites.items():
    for floor_name, floor_data in site_data.get('floors', {}).items():
        for switch_name, switch_config in floor_data.get('switches', {}).items():
            model = switch_config.get('model', 'Unknown')
            if 'N3248' in model:
                n3248_switches.append({
                    'site': site_name,
                    'floor': floor_name,
                    'name': switch_name,
                    'model': model,
                    'ip': switch_config.get('ip_address', ''),
                    'series': switch_config.get('series', 'Unknown')
                })

print(f"Dell N3248 switches found: {len(n3248_switches)}")
print("\nDetailed list:")
for i, switch in enumerate(n3248_switches[:10], 1):
    print(f"{i:2d}. {switch['site']}/{switch['floor']}: {switch['name']}")
    print(f"    IP: {switch['ip']}, Model: {switch['model']}")
    print(f"    Series: {switch['series']}")
    print()

if len(n3248_switches) > 10:
    print(f"... and {len(n3248_switches) - 10} more")
