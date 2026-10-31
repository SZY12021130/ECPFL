# esafl_eshe: Multi-Key HE Backend for ECPFL

This directory contains a Python-accessible multi-key homomorphic encryption backend for ECPFL, built by wrapping the xMK-CKKS library from the MASER framework.

## What this package is

- A Python wrapper around MASER's `xmkckks.dll` (Go-implemented multi-key CKKS).
- Provides key generation, per-client encryption, homomorphic aggregation, partial decryption, and plaintext decoding.
- Designed to be plugged into ECPFL's training pipeline as a drop-in replacement for the single-key TenSEAL backend.

## What this package is NOT

- It is **not** a Python re-implementation of ESAFL's C++ `MKHE-V3` library.
- It does **not** provide ESAFL's one-step decryption. The underlying xMK-CKKS uses **distributed decryption**: each client produces a partial decryption share, and the server aggregates all shares to recover the plaintext.
- It is **not** bit-compatible with ESAFL's ESHE parameter choices. Parameter defaults are hardcoded inside the compiled `xmkckks.dll`.

## Decryption model

The wrapper exposes the following workflow, which matches xMK-CKKS / Chen-Kim-Kim-Song multi-key CKKS:

1. **Setup**: server aggregates all client public keys into a joint public key.
2. **Encrypt**: each client encrypts its plaintext vector under the joint public key.
3. **Aggregate**: server homomorphically sums ciphertexts from multiple clients.
4. **Partial decrypt**: each client locally produces a partial decryption share from the aggregated ciphertext.
5. **Decode**: server aggregates all partial shares and decodes the result.

If your paper requires ESAFL-style one-step decryption (each client decrypts locally with the summed global key `S = sum_i s_i`), this backend cannot satisfy that requirement. You will need either:

- a custom implementation of ESAFL's ESHE (e.g., in C++ with NTL/GMP), or
- a Python prototype using small RLWE parameters (too slow for full-scale FL experiments).

## Usage example

```python
from esafl_eshe import ESHEManager
import numpy as np

num_clients = 5
slot_size = 4096

mgr = ESHEManager(num_clients=num_clients, slot_size=slot_size)
mgr.setup()

plaintexts = [np.random.randn(slot_size).tolist() for _ in range(num_clients)]
cts = [mgr.encrypt(i, pt) for i, pt in enumerate(plaintexts)]
agg_ct = mgr.aggregate(cts)

decoded = mgr.full_decrypt(agg_ct)
expected = sum(np.array(pt) for pt in plaintexts)

print("Decoded sum (first 10):", decoded[:10])
print("Expected sum (first 10):", expected[:10])
```

## Running tests

```bash
cd E:\GithubProjects\ckks_fed_robustness
python -m pytest esafl_eshe/tests/test_basic.py -v
```

Or directly:

```bash
python esafl_eshe/tests/test_basic.py
```

## Integration into the ECPFL pipeline

To run an experiment with the real multi-key backend, set in your config:

```yaml
esafl:
  enabled: true
  mode: "NATIVE"
```

and make sure sparsification is disabled (full parameter upload):

```yaml
ckks:
  sparsification:
    strategy: "none"
```

Then run as usual:

```bash
python main.py --config configs/test_esafl_native.yaml
```

In NATIVE mode:
- The server distributes the plaintext global model (no single-key TenSEAL encrypted global state).
- Each client encrypts its local update under the multi-key joint public key using `ESHEManager`.
- The server homomorphically aggregates the updates.
- The server collects a partial decryption share from each participating client and decodes the aggregated update.
- The server applies the decoded update to the global model.

A working example config is provided at `configs/test_esafl_native.yaml`.

## Files

- `__init__.py`: Package exports.
- `core.py`: `ESHEManager` class implementing multi-key CKKS operations.
- `utils.py`: Helper functions for padding and chunking plaintexts.
- `tests/test_basic.py`: End-to-end tests for encryption, aggregation, and decryption.
- `README.md`: This file.
