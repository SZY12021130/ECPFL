# 五基线全模型密文大小对比

口径：按 `AAAAA_Rework` 中各基线的默认加密配置计算一次完整模型上传的密文总大小。

| Dataset | Model | Params | FedAvg+CKKS (#ct / MB) | FedPHE (#ct / MB) | MASER (#ct / MB) | ESAFL (#ct / MB) | ECPFL (#ct / MB) |
|---|---|---|---|---|---|---|---|
| MNIST | LeNet | 44,426 | 11 / 3.508 | 2 / 0.638 | 6 / 1.913 | 6 / 0.375 | 11 / 0.328 |
| FMNIST | CNN | 39,786 | 10 / 3.189 | 1 / 0.319 | 5 / 1.595 | 5 / 0.312 | 10 / 0.298 |
| CIFAR-10 | ResNet-20 | 272,186 | 67 / 21.367 | 7 / 2.232 | 34 / 10.843 | 34 / 2.125 | 67 / 1.996 |
| SVHN | ResNet-32 | 460,618 | 113 / 36.037 | 12 / 3.827 | 57 / 18.178 | 57 / 3.562 | 113 / 3.366 |

## 参数说明
- FedAvg+CKKS：poly_modulus_degree=8192、coeff_mod_bit_sizes=[60,40,40,60]，单密文 334,401 B，密传全部参数。
- FedPHE：同 CKKS 加密参数，sparsity_rate=0.1（batch-level top-10%）。
- MASER：同 CKKS 加密参数，topk_ratio=0.5（参数级保留 50%）。
- ESAFL PUREPY EP：n=4096、logp=56、logq0=10、N=25，EP 位打包后每密文 8,192 值，单密文 65,536 B。
- ECPFL：n=4096、logQ≈61，单 R_Q 多项式密文 31,232 B，每密文 4,096 值。