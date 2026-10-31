import sys

with open('ckks_fed/tee_simulator.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''        for j in range(num_batches):
            if mask[j] == 1 and ciphertexts[j] is not None:
                ct = ts.CKKSVector.load(ctx, ciphertexts[j])
                decrypted = ct.decrypt()
                # \u9664\u4ee5\u805a\u5408\u6743\u91cd W_j \u5f97\u5230\u52a0\u6743\u5e73\u5747
                W_j = agg_weights[j]
                if W_j > 1e-12:
                    avg_batch = np.array(decrypted, dtype=np.float64) / W_j
                else:
                    avg_batch = np.zeros(self.batch_size, dtype=np.float64)
                aggregated_batches.append(avg_batch)
            else:
                aggregated_batches.append(np.zeros(self.batch_size, dtype=np.float64))'''

new_block = '''        for j in range(num_batches):
            if mask[j] == 1 and ciphertexts[j] is not None:
                ct = ts.CKKSVector.load(ctx, ciphertexts[j])
                decrypted = ct.decrypt()
                W_j = agg_weights[j]
                dec_norm = float(np.linalg.norm(np.array(decrypted, dtype=np.float64)))
                if j == 0 or dec_norm > 1e6:
                    print("[DEBUG DECRYPT] batch=%d decrypted_norm=%.2e W_j=%.2f" % (j, dec_norm, W_j))
                if W_j > 1e-12:
                    avg_batch = np.array(decrypted, dtype=np.float64) / W_j
                else:
                    avg_batch = np.zeros(self.batch_size, dtype=np.float64)
                aggregated_batches.append(avg_batch)
            else:
                aggregated_batches.append(np.zeros(self.batch_size, dtype=np.float64))'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('ckks_fed/tee_simulator.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('OK')
else:
    print('Block not found')
