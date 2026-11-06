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

---

# ESAFL PUREPY Mode (Pure-Python ESHE Replication)

## TL;DR

Setting `esafl.mode: "PUREPY"` runs the FL pipeline on a pure-Python
replication of the ESHE scheme **and the EP packing mechanism** from the ESAFL
paper (arXiv:2305.08599, Sec. IV / Sec. V-B2), implemented in `ckks_fed/eshe.py`
and `ckks_fed/packing.py` (`ESHEEPPacking`). No Go DLL / TenSEAL ciphertexts
are involved on the ESHE path: clients encrypt EP-packed integer polynomials
into `R_q = Z_q[X]/(X^n+1)`; the server aggregates **in the ciphertext
domain** (EP.Eval, coefficient-wise summation); one-shot decryption recovers
per-slot integer sums; dividing by N yields the averaged update (paper-style
uniform aggregation).

## Correspondence to the paper's ESHE structure

| Paper ESHE              | PUREPY implementation |
|-------------------------|-----------------------|
| Ring `R_q`, n power of 2 | `RingContext(n)` with CRT representation `Q = q1*q2` (two 31-bit NTT-friendly primes, `q_i = 1 mod 2n`); negacyclic multiplication via psi-twisted NTT (numpy, int64 overflow-free) |
| Plain modulus p < q     | `p = 2^esafl.logp` (default 50), `ESHEParameters` |
| Client key `s_i` from `chi_s` | `PurePyESHE.register_client()` -> ternary `{-1,0,1}^n` |
| Shared key `s = sum s_i` | maintained by the backend (trusted-AS role) |
| PRPG(t, B)              | `PRPG(seed, counter)` — deterministic regeneration from `numpy.random.SeedSequence`; **structurally equivalent but not bit-compatible** with a cryptographic PRG |
| Enc: `[a^t*s_i + p*e_i + m_i]_q` | `PurePyESHE.encrypt_chunk(client_id, m, counter)`; `e_i` centered binomial (`esafl.eta`, default 4) |
| Eval: `C = sum ct_i`    | `PurePyESHE.aggregate()` — coefficient-wise addition, **ciphertext-domain aggregation** |
| Dec: `[[C - a^t*s]_q]_p` | `PurePyESHE.decrypt()` — mod Q then mod p, noise term vanishes exactly (no rescale/relinearize/bootstrapping) |

## EP packing (paper Sec. V-B2) — `ESHEEPPacking`

Paper formulas (arXiv:2305.08599, Sec. V-B2, Eq. 7-12), confirmed against the
published HTML version:

- **EP.Setup(PP, log q0, N) -> (T, pad)**
  - `pad = ceil(log N) + 1` — carry headroom so homomorphic addition never
    overflows a slot's bit field. Example: N = 25 -> pad = 6.
  - `T = floor(log p / (log q0 + pad))` — slots per coefficient.
    Example: log p = 50, log q0 = 10 -> T = floor(50/16) = 3.
- **EP.EcdPack** (Eq. 8-9): each coefficient beta_j of the plaintext
  polynomial holds T slots of `(pad + log q0)` bits; slot 1 sits at the most
  significant bits. The paper packs **T-1 encoded message polynomials plus one
  zero polynomial** (Fig. 1 caption: "(T-1) x n real numbers are first encoded
  and then packed"), i.e. per-coefficient data capacity is **T-1 values**
  (with the example parameters: 2 values/coefficient, 4096*2 = 8192 values
  per ciphertext at n = 4096).
  - Message encoding: the paper uses CKKS canonical embedding
    `z_i = [floor(p*phi^-1(z_i))]_{q0}`; PUREPY uses direct symmetric
    quantization to unsigned integers `u in [0, 2^logq0 - 1]`
    (`u = round(clip(v)/scale) + max_q`). Both are mod-q0 integer coefficient
    polynomials; for the additive homomorphism the semantics are identical,
    and the direct encoding is exact (no FFT round-off).
- **EP.Eval** (Eq. 12): `m_add = sum_i m_i`. Because `pad = ceil(log N)+1`,
  each slot sum satisfies `sum u < N*2^logq0 < 2^(logq0+pad)`, so slots never
  bleed into each other and `sum beta_j < 2^{T(pad+logq0)} <= p` — the summed
  plaintext survives the mod-p decryption untouched.
- **Aggregation -> average**: after one-shot decryption each slot holds the
  exact integer sum of the N clients' encoded values; subtract `N*max_q`,
  divide by N, multiply by `scale` -> averaged update. This is the paper's
  uniform average (equal client weights); unequal data-size weighting is not
  supported on the summed-ciphertext path (same as the paper's EP.Eval).

**Shared quantization scale**: EP.Eval correctness requires all clients to
quantize with the *same* scale. Configure `packing.quant_clip` (the clip
value; `scale = quant_clip / max_q`); without it the packer falls back to
per-pack adaptive scales, which is only valid for `num_sum = 1` decryption
(server-encrypted global state). Server-side re-encryption of the global
model uses the adaptive scale automatically (`skip_sparsification=True`).

`packing.quant_bits` doubles as `log q0`. `packing.slots2` / `packing.pad_bits`
are **not used** under PUREPY+EP (pad and T are derived from N and logp) — a
warning is logged if they are set.

## Fixed-point encoding variant (`esafl.encoding: "fixed"`)

An alternative message encoding for PUREPY that keeps the paper's single-
ciphertext ESHE structure (`ct = a^t·s_i + e + m`, one-shot decryption
`ct − a^t·s`, multi-key `s = Σ s_i`, PRPG-regenerated `a^t`) but replaces the
EP bit-packing with a CKKS-style fixed-point encoding:

- **Encoding**: `m_j = round(x_j · Δ)`, one float value per coefficient
  (`Δ = 2^esafl.delta_scale`, default `2^20`). n values per ciphertext
  (EP packs `(T−1)·n` values into the same ciphertext).
- **Encryption**: `ct = [a^t·s_i + e + m]_Q` — the noise term is the raw small
  integer `e ∈ [−eta, eta]` (no `p̃·e`, no mod-p semantics).
- **Decryption**: `x̂_j = [ct − mask]_Q / Δ`. Error per coefficient ≤
  `(eta + 0.5)/Δ ≈ 5e-6`; after summing N clients ≤ `N·(eta+0.5)/Δ ≈ 1e-4`
  — roughly two orders of magnitude better than EP's `1/(2^logq0−1)`.
- **Aggregation**: same ciphertext-domain summation as EP.Eval (scale does not
  grow; only addition is used, no rescaling). The summed coefficients are
  integer sums `Σ round(x_i·Δ)`; divide by N and by Δ to get the average.
- **No quant_clip needed**: Δ is fixed globally, so all clients share the
  encoding scale by construction (the EP cross-client scale consistency
  requirement disappears). The only bound is `|x| < Q/(8Δ)` (≈ 1.4e11 for
  Q≈2^60, Δ=2^20), which never binds for FL updates.
- **Ciphertext size (paper accounting)**: per ESAFL, the mask polynomial is
  not transmitted (`a^t` is publicly regenerated via PRPG(t, B) and `s` is the
  shared decryption key), so only the coeffs polynomial counts: 8·n·2 bytes
  (CRT pair, int64) = 64 KB per ciphertext at n = 4096, i.e. **8 bytes per
  value** (EP: 128 KB coeffs+mask ≈ 16 B/value, or 64 KB coeffs-only ≈ 8 B/
  value at 2 values/coefficient). At n = 4096 a 44,426-param LeNet needs
  ceil(44426/4096) = **11 ciphertexts of 64 KB = 704 KB per client**
  (EP: 6 × 128 KB = 768 KB).

Trade-off vs EP: 2× fewer values per ciphertext (n vs (T−1)·n) → ~2× more
ciphertexts for the same model, but much higher precision and no quant_clip
tuning. Set `esafl.encoding: "fixed"` (default remains `"ep"`; EP behavior
unchanged).

Implementation: `PurePyESHE(encoding="fixed", delta_scale=...)` with
`encrypt_chunk_fixed` / `decrypt_fixed(_ints)`; packing in
`ESHEFixedPacking` (flatten → n-sized chunks; rounding happens in the eshe
layer). Aggregation, subtraction, extended decryption and the server paths are
shared with the EP mode.


## Cross-round (extended) decryption

Each ciphertext carries its *mask* polynomial (`a^t*s_i` at encryption,
summed on aggregation, subtracted on ciphertext subtraction). Decrypting any
accumulated delta is simply `[[ct - mask]_Q]_p`, which realizes the paper's
`[[ct - Delta_a*s]_q]_p` with `Delta_a = sum(a^(r_j) - a^(r_(j-1)))`
automatically. `ESAFLAdapter.extended_decrypt()` therefore works for PUREPY
without extra round context. Ciphertext *deltas* (differences of packed
codes) carry no unsigned zero-point, so the EP unpacker is told
`zero_point = 0` for deltas (`__zero_point__` flag set by
`subtract_encrypted_updates`).

## Integration points

- `ckks_fed/packing.py` — `ESHEEPPacking`: `pack()` (EP.EcdPack),
  `unpack_average()` (EP.DcdUnpk + average), `create_zero_chunk()`.
- `ckks_fed/crypto.py`
  - `CKKSManager.__init__` creates `self.purepy_eshe` and `self.ep_packing`
    when `esafl.mode == "PUREPY"` (EP params derived from `packing.quant_bits`,
    `esafl.logp`, and `esafl.num_clients` injected by `main.py`).
  - `encrypt_model_update()` PUREPY branch: EP-packs the update (fixed
    `quant_clip` scale for client uploads) and ESHE-encrypts each chunk with
    the client's `s_i` and `counter = round_num`.
  - `_aggregate_sparse_updates()` PUREPY branch: **EP.Eval ciphertext-domain
    summation** (`PurePyESHE.aggregate`), no server-side decryption; result
    carries `__num_sum__ = N`.
  - `decrypt_model_update()` PUREPY branch: one-shot decrypt + EP
    `unpack_average(..., num_sum=__num_sum__)`.
  - `subtract_encrypted_updates()` and `compute_encrypted_update_size()` have
    PUREPY branches.
- `ckks_fed/esafl_crypto.py` — `ESAFLAdapter.extended_decrypt` handles PUREPY.
- `main.py` — PUREPY clients train on the plaintext global model (like
  NATIVE) and encrypt uploads with their own `s_i`; `num_clients` is injected
  into the esafl config for EP parameter derivation.
- Config: `esafl.mode: "PUREPY"`, optional `esafl.logp` (default 50),
  `esafl.eta` (default 4); `packing.quant_bits` = log q0,
  `packing.quant_clip` (recommended). `client_sampling_rate` must be 1.0
  (ESHE full-participation constraint).

## Known differences / caveats

1. **numpy PRG is not bit-compatible** with the paper's PRG (documented
   above).
2. **Uniform aggregation only**: EP.Eval sums ciphertexts; unequal FedAvg
   weights are not supported (weights are validated and a warning is logged
   if they differ). Same semantic model as the paper's cross-silo setting.
3. **Message encoding**: direct symmetric quantization into unsigned
   `log q0`-bit integers instead of the paper's CKKS canonical embedding
   `[floor(p*phi^-1(z))]_{q0}` — equivalent for additive homomorphism, exact
   (no FFT).
4. **Full participation (ESHE-PS)**: the paper requires unsampled clients to
   upload `Enc(0)`. PUREPY provides `encrypt_zero()`; in the current
   integration the trusted-AS backend tracks each ciphertext's mask, so
   decryption already matches the participating set — `Enc(0)` padding is
   available but not required by the wiring.
5. **Performance**: NTT-based multiplication at n = 4096 costs ~2 ms per
   polynomial product; a 25-client MNIST round adds only a few seconds.

## Verified

- `python -m pytest tests/test_eshe_purepy.py -v` — 20 tests green (ring ops
  vs naive convolution, 1/5/25-client Enc->aggregate->Dec round-trips,
  cross-round delta decryption, EP setup formulas, EP pack/unpack round-trip,
  EP ciphertext-sum aggregation incl. all-max carry boundary, CKKSManager e2e
  over the ciphertext-domain aggregation path, adapter extended decrypt, plus
  fixed-mode round-trip/sum-average/bounds/manager-e2e).
- `python main.py --config <mnist PUREPY EP, 2 rounds>` runs end-to-end with
  accuracy in the normal MNIST-LeNet range (~82% after round 1, ~94% after
  round 2).
