import json
import os

ROOT = r"E:\GithubProjects\ckks_fed_robustness"
path = os.path.join(ROOT, "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist/metrics.json")

with open(path) as f:
    d = json.load(f)

# MASER 是 3 轮一个周期：MASK → ENC → DEC
# 只有 ENC 轮有加密上传，只有 DEC 轮有部分解密上传
print("MASER MNIST 3 轮周期分析:")
for r in range(0, 9):
    print(f"  Round {r}: ct_upload={d['maser_ct_upload'][r]:.0f}, partial_dec={d['maser_partial_dec_upload'][r]:.0f}")

# 检查哪些轮次有加密上传（非零）
enc_rounds = [r for r in range(50) if d['maser_ct_upload'][r] > 0]
dec_rounds = [r for r in range(50) if d['maser_partial_dec_upload'][r] > 0]
print(f"\n加密上传轮次: {enc_rounds}")
print(f"部分解密轮次: {dec_rounds}")

# 计算 single_ct
n_sel = 25
nb_up = d['num_ciphertexts'][0]
single_ct = d['maser_ct_upload'][0] / n_sel / nb_up
print(f"\nsingle_ct = {single_ct:.0f} bytes")

# 检查 plaintext_size 和 maser_plaintext_download 的关系
print(f"\nplaintext_size[0] = {d['plaintext_size'][0]} bytes")
print(f"maser_plaintext_download[0] = {d['maser_plaintext_download'][0]} bytes")
print(f"maser_plaintext_download / plaintext_size = {d['maser_plaintext_download'][0] / d['plaintext_size'][0]:.2f}")
