import os
import shutil

input_dir = 'skps'
output_dir = 'flattened'
os.makedirs(output_dir, exist_ok=True)

for website in os.listdir(input_dir):
    website_path = os.path.join(input_dir, website)
    if not os.path.isdir(website_path):
        continue
    for filename in os.listdir(website_path):
        if filename.endswith('.skp'):
            src = os.path.join(website_path, filename)
            dst = os.path.join(output_dir, f'{website}__{filename}')
            shutil.copy2(src, dst)

print('Flattening complete.')
