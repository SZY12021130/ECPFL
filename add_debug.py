import sys

# Add debug prints to tee_simulator.py
with open('ckks_fed/tee_simulator.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_block = '''        else:
            selected_indices = list(range(num_batches))
            mask = [1] * num_batches

            new_global_batches = [
                old_batches[j] + aggregated_delta[j]
                for j in range(num_batches)
            ]
            self.old_global_plain_batches = new_global_batches

            t0 = time.time()
            encrypted_selected = []
            for plain_batch in new_global_batches:
                ct = ts.ckks_vector(
                    self.context,
                    np.array(plain_batch, dtype=np.float64),
                    scale=self.context.global_scale
                )
                encrypted_selected.append(ct.serialize())
            self.tee_reencrypt_time += time.time() - t0

            logger.info(
                f"TEE post-process | compression=OFF | selected={num_batches}/{num_batches} "
                f"(100.0%) | full aggregation, no residual"
            )'''

new_block = '''        else:
            selected_indices = list(range(num_batches))
            mask = [1] * num_batches

            # DEBUG
            for j in range(num_batches):
                d_norm = float(np.linalg.norm(aggregated_delta[j]))
                o_norm = float(np.linalg.norm(old_batches[j]))
                if d_norm > 1000 or o_norm > 1000:
                    print("[DEBUG TEE] batch=%d old_norm=%.2f delta_norm=%.2f" % (j, o_norm, d_norm))
            # END DEBUG

            new_global_batches = [
                old_batches[j] + aggregated_delta[j]
                for j in range(num_batches)
            ]
            self.old_global_plain_batches = new_global_batches

            t0 = time.time()
            encrypted_selected = []
            for plain_batch in new_global_batches:
                ct = ts.ckks_vector(
                    self.context,
                    np.array(plain_batch, dtype=np.float64),
                    scale=self.context.global_scale
                )
                encrypted_selected.append(ct.serialize())
            self.tee_reencrypt_time += time.time() - t0

            # DEBUG
            ng_norms = [float(np.linalg.norm(b)) for b in new_global_batches]
            print("[DEBUG TEE] compression=OFF new_global_norms max=%.2f min=%.2f" % (max(ng_norms), min(ng_norms)))
            # END DEBUG

            logger.info(
                f"TEE post-process | compression=OFF | selected={num_batches}/{num_batches} "
                f"(100.0%) | full aggregation, no residual"
            )'''

if old_block in content:
    content = content.replace(old_block, new_block)
    with open('ckks_fed/tee_simulator.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Debug prints added to tee_simulator.py')
else:
    print('ERROR: Block not found')
    sys.exit(1)
