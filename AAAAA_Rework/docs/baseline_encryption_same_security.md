# 五基线加密方法与密文大小（同 logQ=61 安全级别对照）

口径：以 ECPFL 的 n=4096、logQ≈61 为基准；CKKS 取 poly_modulus_degree=8192、slot_count=4096、logQ=61，得到标准 (c0,c1) 双多项式密文。ESAFL EP 与 ECPFL 同单多项式结构，但 EP 位打包使每密文承载值翻倍。

| Method | Encryption Method | Single ct (B) | Values/ct | MNIST (ct / MB) | FMNIST (ct / MB) | CIFAR-10 (ct / MB) | SVHN (ct / MB) |
|---|---|---:|---:|---:|---:|---:|---:|
| FedAvg+CKKS | Single-key CKKS (c0,c1), N=8192, logQ=61 | 124,928 | 4,096 | 11 / 1.311 | 10 / 1.191 | 67 / 7.982 | 113 / 13.463 |
| FedPHE | Single-key CKKS + batch-level Top-ζ mask | 124,928 | 4,096 | 11 / 1.311 | 10 / 1.191 | 67 / 7.982 | 113 / 13.463 |
| MASER | xMK-CKKS / param-level mask + partial decrypt | 124,928 | 4,096 | 11 / 1.311 | 10 / 1.191 | 67 / 7.982 | 113 / 13.463 |
| ESAFL | Pure-Python ESHE EP packing, n=4096, logQ=61 | 31,232 | 8,192 | 6 / 0.179 | 5 / 0.149 | 34 / 1.013 | 57 / 1.698 |
| ECPFL | Custom single-ct RLWE, n=4096, logQ=61 | 31,232 | 4,096 | 11 / 0.328 | 10 / 0.298 | 67 / 1.996 | 113 / 3.366 |