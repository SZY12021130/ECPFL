import glob
import re

for f in sorted(glob.glob('accuracy_baseline/*/config/config_*.yaml')):
    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()

    new_content, n = re.subn(
        r'(system:\s*\n(?:.*\n)*?\s+num_epochs:\s*)\d+',
        r'\g<1>3',
        content,
        flags=re.MULTILINE
    )

    if n > 0:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(new_content)
        print(f"Updated: {f}")

print("\nDone.")
