import os

flattened_dir = 'flattened'
json_dir = 'json'

# Get base names of all JSON files (without extension)
json_basenames = {os.path.splitext(f)[0] for f in os.listdir(json_dir) if f.endswith('.json')}

# Iterate over .skp files in flattened, remove if no matching .json basename
for f in os.listdir(flattened_dir):
    if f.endswith('.skp'):
        base = os.path.splitext(f)[0]
        if base not in json_basenames:
            os.remove(os.path.join(flattened_dir, f))

print('Cleanup complete.')
