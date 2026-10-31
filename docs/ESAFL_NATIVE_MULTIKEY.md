# ESAFL NATIVE Multi-Key CKKS Backend

## TL;DR

ECPFL now has a real, Python-callable multi-key homomorphic-encryption backend.
Setting `esafl.mode: "NATIVE"` runs the full FL pipeline on top of the
`esafl_eshe` wrapper around MASER's xMK-CKKS Go library, instead of on the
single-key TenSEAL backend.

## Why this was necessary

The original ECPFL implementation used TenSEAL for all encrypted FL paths.
TenSEAL is a single-key CKKS library: all clients share the same secret key,
which means the security claim of "multi-key" encryption was only a simulation.

The ESAFL C++ `MKHE-V3` library (the paper's original backend) is only
available as Linux ELF binaries in this repository, with no headers or source,
so it cannot be compiled or called on Windows.

The honest and reproducible path is to use the available xMK-CKKS Go DLL from
the MASER baseline. It is a true multi-key CKKS implementation (Chen-Kim-Kim-Song
style, Lattigo/Go), supports per-client keys, homomorphic aggregation, and
distributed partial decryption.

## What changed

1. **`esafl_eshe/` package**  
   New wrapper around `MASER-main/xmkckks_wrapper.py` exposing a clean API:
   - `ESHEManager.setup()` — aggregate client public keys into a joint public key.
   - `ESHEManager.encrypt(client_idx, values)` — encrypt a plaintext vector.
   - `ESHEManager.aggregate(cts)` — homomorphically sum ciphertexts.
   - `ESHEManager.partial_decrypt(client_idx, agg_ct)` — produce a partial share.
   - `ESHEManager.decode(shares, client_indices)` — aggregate shares and decode.

2. **`ckks_fed/crypto.py`**  
   - Added `self.eshe` backend injection.
   - Added ESAFL NATIVE encryption branch in `encrypt_model_update()`.
   - Added ESAFL NATIVE aggregation branch in `_aggregate_sparse_updates()`.
   - Added `decrypt_esafl_native_multikey()` for server-side decoding.

3. **`ckks_fed/server.py`**  
   - Added `update_global_model_esafl_native_multikey()` which decodes the
     aggregated multi-key ciphertext and applies the plaintext update.

4. **`main.py`**  
   - Added `_ensure_eshe_manager()` to create/reuse an `ESHEManager` instance.
   - In NATIVE mode the server distributes a plaintext global model and clients
     encrypt uploads with the multi-key backend.
   - After aggregation the server collects partial decryption shares from the
     selected clients and decodes.

5. **`ckks_fed/xmkckks_manager.py`**  
   - Fixed the default `client_id_to_idx` mapping (was 1-based and collided with
     0-based indices, causing ciphertexts to be encrypted under the wrong key).
   - Fixed `decode_partial_decryptions()` to truncate the decoded vector to
     `slot_size` (the Go library returns `2 * slot_size` floats).

6. **Configuration**  
   - `esafl.mode: "NATIVE"` now enables the real backend.
   - Added `configs/test_esafl_native.yaml` as a working smoke-test config.

## Verified end-to-end

`python main.py --config configs/test_esafl_native.yaml` completes 5 rounds of
MNIST + LeNet with 5 clients, reaching **98.31%** test accuracy. All
`esafl_eshe/tests/test_basic.py` tests pass.

## Important caveats

- **Decryption model**: xMK-CKKS uses distributed partial decryption, not
  ESAFL's one-step decryption with a summed global key `S = sum_i s_i`. The
  paper's protocol description should be updated to match (partial-decryption
  threshold style).

- **Full upload only**: The current NATIVE integration disables client-side
  sparsification and global-mask voting. Each client uploads its full model
  update. Reducing communication would require adding compensatory/zero
  ciphertexts for inactive clients or implementing multi-key compatible
  sparse encoding.

- **Weighted FedAvg**: xMK-CKKS supports homomorphic addition but not scalar
  multiplication. The current implementation averages the decoded sum uniformly
  by the number of participating clients. Data-size weighting would require
  clients to pre-weight their plaintexts before encryption.

- **Global model distribution**: In NATIVE mode the server sends the plaintext
  global model to clients. The multi-key property protects individual client
  updates, not the global model itself.

## Next steps / open work

- Implement compensatory ciphertexts for inactive clients so that the
  ciphertext can be decrypted with the full client set even under partial
  participation.
- Support sparsification / global-mask voting in NATIVE mode.
- Add communication-cost accounting that reflects multi-key ciphertext growth.
- Update the paper's security protocol description from one-step decryption to
  partial-decryption aggregation.
