import json
import os

ROOT = r"E:\GithubProjects\ckks_fed_robustness"
path = os.path.join(ROOT, "accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist/metrics.json")
with open(path) as f:
    d = json.load(f)

print(f"num_selected per round first 10: {[len(x) if x else 0 for x in d.get('selected_clients', [])[:10]]}")
print(f"upload_cost first 10: {d['upload_cost'][:10]}")
print(f"download_cost first 10: {d['download_cost'][:10]}")
print(f"num_ciphertexts unique: {sorted(set(d['num_ciphertexts']))}")
print(f"aggregated_ciphertexts unique: {sorted(set(d.get('aggregated_ciphertexts', [])))}")
print(f"single_ct from upload = {d['upload_cost'][0] / 25 / 2:.0f}")
print(f"full_blocks from download = {d['download_cost'][0] / 25 / (d['upload_cost'][0]/25/2):.1f}")
