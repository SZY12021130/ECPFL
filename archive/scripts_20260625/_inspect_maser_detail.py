import json
import os

ROOT = r"E:\GithubProjects\ckks_fed_robustness"
path = os.path.join(ROOT, "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist/metrics.json")

with open(path) as f:
    d = json.load(f)

print("MASER MNIST metrics:")
print(f"  num_ciphertexts[0:5] = {d['num_ciphertexts'][0:5]}")
print(f"  aggregated_ciphertexts[0:5] = {d['aggregated_ciphertexts'][0:5]}")
print(f"  maser_ct_upload[0:5] = {d['maser_ct_upload'][0:5]}")
print(f"  maser_partial_dec_upload[0:5] = {d['maser_partial_dec_upload'][0:5]}")
print(f"  plaintext_size[0:5] = {d['plaintext_size'][0:5]}")
print(f"  maser_plaintext_download[0:5] = {d['maser_plaintext_download'][0:5]}")

# 计算 single_ct
n_sel = 25  # 客户端数
nb_up = d['num_ciphertexts'][0]
single_ct = d['maser_ct_upload'][0] / n_sel / nb_up
print(f"\n  single_ct = {single_ct:.0f} bytes")
print(f"  plaintext_size = {d['plaintext_size'][0]} bytes")
print(f"  model_size / single_ct = {d['plaintext_size'][0] / single_ct:.2f}")

# 检查 TT 计算
print("\n  检查 TT 计算:")
print(f"  upload_cost[0] = {d['upload_cost'][0]}")
print(f"  download_cost[0] = {d['download_cost'][0]}")
print(f"  maser_ct_upload[0] + maser_partial_dec_upload[0] = {d['maser_ct_upload'][0] + d['maser_partial_dec_upload'][0]}")
