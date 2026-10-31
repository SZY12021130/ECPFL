import glob
import re

for f in sorted(glob.glob('accuracy_baseline/esafl/config/config_*.yaml')):
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()

    # Replace num_clients: 50 -> 25
    content = re.sub(r'(num_clients:\s*)50', r'\g<1>25', content)
    # Replace client_sampling_rate: 0.5 -> 1.0
    content = re.sub(r'(client_sampling_rate:\s*)0\.5', r'\g<1>1.0', content)

    with open(f, 'w', encoding='utf-8') as fh:
        fh.write(content)
    print(f"Updated: {f}")

print("\nDone. ESAFL num_clients=25, client_sampling_rate=1.0")
