import glob
import re
import os

mapping = {
    'fedphe': 'accuracy_baseline/fedphe/result_fix',
    'fedavg+ckks': 'accuracy_baseline/fedavg+ckks/result_fix',
    'esafl': 'accuracy_baseline/esafl/result_fix',
    'maser': 'accuracy_baseline/maser/result_fix',
}

for f in sorted(glob.glob('accuracy_baseline/*/config/config_*.yaml')):
    # determine baseline name from path
    parts = f.replace('\\', '/').split('/')
    baseline = parts[1]  # e.g. fedphe, fedavg+ckks, esafl, maser
    target_dir = mapping.get(baseline)
    if not target_dir:
        continue

    with open(f, 'r', encoding='utf-8') as fh:
        content = fh.read()

    # Replace results_dir line
    new_content, n = re.subn(
        r'(results_dir:\s*")\.\/[^"]*"',
        rf'\g<1>{target_dir}"',
        content
    )

    if n > 0:
        with open(f, 'w', encoding='utf-8') as fh:
            fh.write(new_content)
        print(f"Updated {f}: results_dir -> {target_dir}")
    else:
        # maybe single quotes or no quotes? try looser pattern
        new_content2, n2 = re.subn(
            r'(results_dir:\s*)[^\n]*',
            rf'\g<1>"{target_dir}"',
            content
        )
        if n2 > 0:
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write(new_content2)
            print(f"Updated {f}: results_dir -> {target_dir}")
        else:
            print(f"WARNING: could not update {f}")

print("\nDone.")
