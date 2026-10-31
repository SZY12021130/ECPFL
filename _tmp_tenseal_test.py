import numpy as np
import tenseal as ts

context = ts.context(ts.SCHEME_TYPE.CKKS, 8192, [60, 40, 40, 60])
context.global_scale = 2**40
context.generate_galois_keys()

for v in [1e10, 1e14, 1e15, 1e20]:
    data = np.array([v, -v], dtype=np.float64)
    ct = ts.ckks_vector(context, data, scale=2**40)
    dec = ct.decrypt()
    print(f'v={v:.0e} -> dec={dec[0]:.6e} err={abs(dec[0]-v):.6e}')

# test inf
import math
try:
    data = np.array([1e308, -1e308], dtype=np.float64)
    ct = ts.ckks_vector(context, data, scale=2**40)
    dec = ct.decrypt()
    print(f'inf test: dec={dec}')
except Exception as e:
    print(f'inf test error: {e}')
