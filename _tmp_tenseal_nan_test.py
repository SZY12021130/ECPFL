import numpy as np
import tenseal as ts

context = ts.context(ts.SCHEME_TYPE.CKKS, 8192, [60, 40, 40, 60])
context.global_scale = 2**40
context.generate_galois_keys()

for val in [float('nan'), float('inf'), -float('inf'), 1e308, -1e308]:
    try:
        data = np.array([val, val], dtype=np.float64)
        ct = ts.ckks_vector(context, data, scale=2**40)
        dec = ct.decrypt()
        print(f'val={val} -> dec={dec}')
    except Exception as e:
        print(f'val={val} -> error: {e}')
