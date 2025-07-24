import json
from collections import Counter

# Load switches.json
with open('switches.json', 'r') as f:
    data = json.load(f)

# Extract all switch models
models = []
sites = data.get('sites', {})
for site_name, site_data in sites.items():
    for floor_name, floor_data in site_data.get('floors', {}).items():
        for switch_name, switch_config in floor_data.get('switches', {}).items():
            model = switch_config.get('model', 'Unknown')
            models.append(model)

# Count models
model_counts = Counter(models)

print(f"Total switches: {len(models)}")
print(f"Total sites: {len(sites)}")
print("\nSwitch Models:")
for model, count in model_counts.most_common():
    print(f"  {model}: {count}")

# Check for N3200 series (Dell N3248)
n3248_count = model_counts.get('Dell N3248', 0)
print(f"\nDell N3248 switches (N3200 series): {n3248_count}")
