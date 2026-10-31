import glob
import re

print('Checking device settings...\n')

for f in sorted(glob.glob('accuracy_baseline/*/config/config_*.yaml')):
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()

    m = re.search(r'device:\s*"([^"]+)"', content)
    device = m.group(1) if m else 'MISSING'

    status = 'OK' if device == 'cuda' else 'NEED FIX'
    print(f'{f}: device={device} [{status}]')
