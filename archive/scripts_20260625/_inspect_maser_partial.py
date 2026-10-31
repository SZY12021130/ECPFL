import json
import os

ROOT = r"E:\GithubProjects\ckks_fed_robustness"
path = os.path.join(ROOT, "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist/metrics.json")

with open(path) as f:
    d = json.load(f)

print("MASER MNIST 通信量分析:")
print(f"  maser_ct_upload[0] = {d['maser_ct_upload'][0]} bytes ({d['maser_ct_upload'][0]/1024/1024:.2f} MB)")
print(f"  maser_partial_dec_upload[0] = {d['maser_partial_dec_upload'][0]} bytes ({d['maser_partial_dec_upload'][0]/1024/1024:.2f} MB)")
print(f"  ratio = {d['maser_partial_dec_upload'][0] / d['maser_ct_upload'][0]:.2f}")

# 计算 single_ct
n_sel = 25
nb_up = d['num_ciphertexts'][0]
single_ct = d['maser_ct_upload'][0] / n_sel / nb_up
print(f"\n  single_ct = {single_ct:.0f} bytes")
print(f"  nb_up = {nb_up}")
print(f"  n_sel = {n_sel}")

# 计算 ③ 的大小
partial_dec_per_client = d['maser_partial_dec_upload'][0] / n_sel
print(f"\n  ③ 每客户端大小 = {partial_dec_per_client:.0f} bytes ({partial_dec_per_client/1024/1024:.2f} MB)")
print(f"  ③ / single_ct = {partial_dec_per_client / single_ct:.1f}")
print(f"  ③ / (nb_up * single_ct) = {partial_dec_per_client / (nb_up * single_ct):.1f}")

# 检查 plaintext_size
print(f"\n  plaintext_size = {d['plaintext_size'][0]} bytes")
print(f"  maser_plaintext_download[0] = {d['maser_plaintext_download'][0]} bytes")
print(f"  maser_plaintext_download / plaintext_size = {d['maser_plaintext_download'][0] / d['plaintext_size'][0]:.1f}")
