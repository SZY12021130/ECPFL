# Performance Table Calculation Methodology

This document shows exactly how every number in `perf_evaluation.tex` was derived.
All source values come from the `report.md` file of each experiment.

## Global settings

- Communication rounds: **50**
- **Batches** and **Communication (MB)** values are **per-round averages** (raw total / 50).
- **Time (s)** values are **50-round totals** (raw total, not divided by 50), so that small per-round download times are not rounded to 0.0.
- Source paths are listed under each method.

## Metric definitions

| Symbol | Meaning | Source / formula |
|---|---|---|
| $N_{\mathrm{up}}$ | Total upload ciphertext batches across all selected clients in all rounds | `Total CT Blocks` line in report.md |
| $N_{\mathrm{agg}}$ | Total server-side aggregated ciphertext batches broadcast | Baselines: `Total Aggregated CTs` line in report.md; we inspect `metrics.json` to determine whether it was logged once or twice per round and divide by that factor. ECPFL: the raw `Total Aggregated CTs` line is 0/absent. ECPFL selects `topk` residual blocks each round; the server aggregates one global ciphertext per selected block, so the number of broadcast aggregated blocks equals the average number of ciphertext blocks uploaded by each selected client per round (`num_ciphertexts` in metrics.json). |
| Up (MB) | Total upload volume | `Total Upload` line, MB value |
| Down (MB) | Total download volume | Baselines: `Total Download` MB. ECPFL: `Effective Download` MB, i.e. the residual fetch volume a selected client is responsible for after prefetching. |
| Up (s) | Serial upload latency (50-round total) | Baselines: raw `CT Upload Time`. ECPFL-RK: raw `CT Upload Time` from the report. Older ECPFL reports without this line split `Total Simulated Comm Time` proportionally by upload volume. |
| Down (s) | Serial download latency (50-round total) | Baselines: raw `CT Download Time`, or `Total Download` time if CT time is missing. ECPFL-RK: raw `CT Download Time` from the report. Older ECPFL reports without this line split `Total Simulated Comm Time` proportionally by effective download volume. |
| TT (s) | Total simulated wall-clock time (50-round total) | Baselines: raw `Total Simulated Time`. ECPFL-RK: raw `Total Simulated Time` (training + encryption + communication). |

## Method/dataset source paths

### FedAvg+CKKS
- **MNIST**: `accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist`  → model = `lenet`
- **FMNIST**: `accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_015145_fashion_mnist`  → model = `cnn_fmnist`
- **CIFAR-10**: `accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_104710_cifar10`  → model = `resnet20`
- **SVHN**: `accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260629_140648_svhn`  → model = `resnet32`

### FedPHE
- **MNIST**: `accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist`  → model = `lenet`
- **FMNIST**: `accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_125524_fashion_mnist`  → model = `cnn_fmnist`
- **CIFAR-10**: `accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_131120_cifar10`  → model = `resnet20`
- **SVHN**: `accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_134815_svhn`  → model = `resnet32`

### ESAFL
- **MNIST**: `accuracy_baseline/esafl/result_fix_pro/experiment_20260622_104429_mnist`  → model = `lenet`
- **FMNIST**: `accuracy_baseline/esafl/result_fix_pro/experiment_20260622_111118_fashion_mnist`  → model = `cnn_fmnist`
- **CIFAR-10**: `accuracy_baseline/esafl/result_fix_pro/experiment_20260622_114557_cifar10`  → model = `resnet20`
- **SVHN**: `accuracy_baseline/esafl/result_fix_pro/experiment_20260622_130213_svhn`  → model = `resnet32`

### MASER
- **MNIST**: `accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist`  → model = `lenet`
- **FMNIST**: `accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist`  → model = `cnn_fmnist`
- **CIFAR-10**: `accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10`  → model = `resnet20`
- **SVHN**: `accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn`  → model = `resnet32`

### ECPFL-RK
- **MNIST**: `accuracy_baseline/ours/result/mnist_rk`  → model = `lenet`
- **FMNIST**: `accuracy_baseline/ours/result/fashion_mnist_rk`  → model = `cnn_fmnist`
- **CIFAR-10**: `accuracy_baseline/ours/result/cifar10_rk`  → model = `resnet20`
- **SVHN**: `accuracy_baseline/ours/result/svhn_rk`  → model = `resnet32`

## Raw totals from reports

| Dataset | Method | Model | $N_{\mathrm{up}}$ | $N_{\mathrm{agg}}$ | Up MB | Down MB | CT Up s | CT Down s | Total Comm s | TT s | Acc % |
|---|---|---|---|---|---|---|---|---|---|---|---|
| MNIST | FedAvg+CKKS | `lenet` | 13750 | 1100 | 4383.87 | 4383.87 | 269.07 | 182.57 | 451.64 | 315.01 | 98.86 |
| FMNIST | FedAvg+CKKS | `cnn_fmnist` | 12500 | 1000 | 3985.09 | 3985.09 | 244.59 | 165.96 | 410.55 | 285.43 | 90.96 |
| CIFAR-10 | FedAvg+CKKS | `resnet20` | 83750 | 6700 | 26699.46 | 26699.46 | 1638.71 | 1111.93 | 2750.65 | 1756.32 | 77.56 |
| SVHN | FedAvg+CKKS | `resnet32` | 143750 | 11500 | 45828.08 | 32536.97 | 2522.70 | 1137.73 | 3660.43 | 3141.61 | 95.24 |
| MNIST | FedPHE | `lenet` | 2500 | 200 | 797.03 | 3133.42 | 48.92 | 130.50 | 179.41 | 201.50 | 98.69 |
| FMNIST | FedPHE | `cnn_fmnist` | 1250 | 100 | 398.55 | 3645.94 | 24.46 | 151.84 | 176.30 | 179.43 | 79.02 |
| CIFAR-10 | FedPHE | `resnet20` | 42500 | 3400 | 13548.73 | 18960.94 | 831.57 | 789.65 | 1621.22 | 1221.47 | 75.77 |
| SVHN | FedPHE | `resnet32` | 72500 | 5800 | 23112.74 | 32567.46 | 1418.58 | 1356.31 | 2774.89 | 2445.11 | 94.44 |
| MNIST | ESAFL | `lenet` | 7500 | 600 | 2390.93 | 2390.93 | 146.75 | 99.57 | 246.32 | 239.98 | 99.11 |
| FMNIST | ESAFL | `cnn_fmnist` | 6250 | 500 | 1992.65 | 1992.65 | 122.30 | 82.99 | 205.29 | 244.43 | 89.51 |
| CIFAR-10 | ESAFL | `resnet20` | 42500 | 3400 | 13549.24 | 13549.24 | 831.60 | 564.28 | 1395.88 | 1402.62 | 81.91 |
| SVHN | ESAFL | `resnet32` | 72500 | 5800 | 23113.26 | 23113.26 | 1418.61 | 962.58 | 2381.19 | 2363.50 | 95.74 |
| MNIST | MASER | `lenet` | 8675 | 694 | 5531.23 | 2977.45 | 339.49 | 124.00 | 463.49 | 466.66 | 99.13 |
| FMNIST | MASER | `cnn_fmnist` | 7475 | 598 | 4766.15 | 2573.86 | 292.54 | 107.19 | 399.73 | 427.77 | 90.66 |
| CIFAR-10 | MASER | `resnet20` | 42450 | 3396 | 27066.40 | 14839.93 | 1661.20 | 618.02 | 2279.22 | 1927.93 | 80.64 |
| SVHN | MASER | `resnet32` | 73700 | 5896 | 46991.57 | 25733.91 | 2884.12 | 1071.71 | 3955.82 | 3308.35 | 95.82 |
| MNIST | ECPFL-RK | `lenet` | 2500 | 0 | 797.00 | 17.28 | 78.62 | 2.31 | 80.93 | 129.89 | 98.29 |
| FMNIST | ECPFL-RK | `cnn_fmnist` | 3750 | 0 | 1195.51 | 21.55 | 52.66 | 0.81 | 53.47 | 95.85 | 87.31 |
| CIFAR-10 | ECPFL-RK | `resnet20` | 58750 | 0 | 18729.71 | 382.91 | 1355.66 | 35.49 | 1391.15 | 1441.36 | 76.51 |
| SVHN | ECPFL-RK | `resnet32` | 100000 | 0 | 31880.43 | 555.29 | 771.91 | 20.26 | 792.17 | 923.17 | 95.20 |

## Values used in the table

- **Batches** and **Communication (MB)**: divide raw totals by 50. Baseline $N_{\mathrm{agg}}$ is divided by the detected logging factor (1 or 2) before averaging.
- ECPFL $N_{\mathrm{agg}}$ is the average number of ciphertext blocks uploaded by each selected client per round (`num_ciphertexts` in metrics.json), because the server aggregates one global ciphertext per selected residual block.
- **Time (s)**: use raw 50-round totals (not divided by 50).

| Dataset | Method | $N_{\mathrm{up}}/N_{\mathrm{agg}}$ | Up/Down MB | Up/Down/TT s |
|---|---|---|---|
| MNIST | FedAvg+CKKS | 275.0 / 11.0 | 87.7 / 87.7 | 269.1 / 182.6 / 315.0 |
| FMNIST | FedAvg+CKKS | 250.0 / 10.0 | 79.7 / 79.7 | 244.6 / 166.0 / 285.4 |
| CIFAR-10 | FedAvg+CKKS | 1675.0 / 67.0 | 534.0 / 534.0 | 1638.7 / 1111.9 / 1756.3 |
| SVHN | FedAvg+CKKS | 2875.0 / 115.0 | 916.6 / 650.7 | 2522.7 / 1137.7 / 3141.6 |
| MNIST | FedPHE | 50.0 / 2.0 | 15.9 / 62.7 | 48.9 / 130.5 / 201.5 |
| FMNIST | FedPHE | 25.0 / 1.0 | 8.0 / 72.9 | 24.5 / 151.8 / 179.4 |
| CIFAR-10 | FedPHE | 850.0 / 34.0 | 271.0 / 379.2 | 831.6 / 789.6 / 1221.5 |
| SVHN | FedPHE | 1450.0 / 58.0 | 462.3 / 651.3 | 1418.6 / 1356.3 / 2445.1 |
| MNIST | ESAFL | 150.0 / 6.0 | 47.8 / 47.8 | 146.8 / 99.6 / 240.0 |
| FMNIST | ESAFL | 125.0 / 5.0 | 39.9 / 39.9 | 122.3 / 83.0 / 244.4 |
| CIFAR-10 | ESAFL | 850.0 / 34.0 | 271.0 / 271.0 | 831.6 / 564.3 / 1402.6 |
| SVHN | ESAFL | 1450.0 / 58.0 | 462.3 / 462.3 | 1418.6 / 962.6 / 2363.5 |
| MNIST | MASER | 173.5 / 6.9 | 110.6 / 59.5 | 339.5 / 124.0 / 466.7 |
| FMNIST | MASER | 149.5 / 6.0 | 95.3 / 51.5 | 292.5 / 107.2 / 427.8 |
| CIFAR-10 | MASER | 849.0 / 34.0 | 541.3 / 296.8 | 1661.2 / 618.0 / 1927.9 |
| SVHN | MASER | 1474.0 / 59.0 | 939.8 / 514.7 | 2884.1 / 1071.7 / 3308.3 |
| MNIST | ECPFL-RK | 50.0 / 2.0 | 15.9 / 0.3 | 78.6 / 2.3 / 129.9 |
| FMNIST | ECPFL-RK | 75.0 / 3.0 | 23.9 / 0.4 | 52.7 / 0.8 / 95.8 |
| CIFAR-10 | ECPFL-RK | 1175.0 / 47.0 | 374.6 / 7.7 | 1355.7 / 35.5 / 1441.4 |
| SVHN | ECPFL-RK | 2000.0 / 80.0 | 637.6 / 11.1 | 771.9 / 20.3 / 923.2 |

## Step-by-step verification per dataset

### MNIST

#### FedAvg+CKKS (lenet)
- Raw report path: `accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_013739_mnist`
- Final accuracy: 98.86%
- $N_{\mathrm{up}}$ total = 13750 → per round = 275.0
- $N_{\mathrm{agg}}$ total = 1100 → raw per round = 22.0; detected logging factor = 2, so unique aggregated batches per round = 11.0
- $N_{\mathrm{agg}}$ total = 1100 → per round = 22.0
- Up volume total = 4383.87 MB → per round = 87.7 MB
- Down volume total = 4383.87 MB → per round = 87.7 MB
- CT Upload Time total = 269.07 s (used as 50-round total in table)
- CT Download Time total = 182.57 s (used as 50-round total in table)
- Total Simulated Time = 315.01 s (used as 50-round TT in the table)

#### FedPHE (lenet)
- Raw report path: `accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_124019_mnist`
- Final accuracy: 98.69%
- $N_{\mathrm{up}}$ total = 2500 → per round = 50.0
- $N_{\mathrm{agg}}$ total = 200 → raw per round = 4.0; detected logging factor = 2, so unique aggregated batches per round = 2.0
- $N_{\mathrm{agg}}$ total = 200 → per round = 4.0
- Up volume total = 797.03 MB → per round = 15.9 MB
- Down volume total = 3133.42 MB → per round = 62.7 MB
- CT Upload Time total = 48.92 s (used as 50-round total in table)
- CT Download Time total = 130.50 s (used as 50-round total in table)
- Total Simulated Time = 201.50 s (used as 50-round TT in the table)

#### ESAFL (lenet)
- Raw report path: `accuracy_baseline/esafl/result_fix_pro/experiment_20260622_104429_mnist`
- Final accuracy: 99.11%
- $N_{\mathrm{up}}$ total = 7500 → per round = 150.0
- $N_{\mathrm{agg}}$ total = 600 → raw per round = 12.0; detected logging factor = 2, so unique aggregated batches per round = 6.0
- $N_{\mathrm{agg}}$ total = 600 → per round = 12.0
- Up volume total = 2390.93 MB → per round = 47.8 MB
- Down volume total = 2390.93 MB → per round = 47.8 MB
- CT Upload Time total = 146.75 s (used as 50-round total in table)
- CT Download Time total = 99.57 s (used as 50-round total in table)
- Total Simulated Time = 239.98 s (used as 50-round TT in the table)

#### MASER (lenet)
- Raw report path: `accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist`
- Final accuracy: 99.13%
- $N_{\mathrm{up}}$ total = 8675 → per round = 173.5
- $N_{\mathrm{agg}}$ total = 694 → raw per round = 13.9; detected logging factor = 2, so unique aggregated batches per round = 6.9
- $N_{\mathrm{agg}}$ total = 694 → per round = 13.9
- Up volume total = 5531.23 MB → per round = 110.6 MB
- Down volume total = 2977.45 MB → per round = 59.5 MB
- CT Upload Time total = 339.49 s (used as 50-round total in table)
- CT Download Time total = 124.00 s (used as 50-round total in table)
- Total Simulated Time = 466.66 s (used as 50-round TT in the table)

#### ECPFL-RK (lenet)
- Raw report path: `accuracy_baseline/ours/result/mnist_rk`
- Final accuracy: 98.29%
- $N_{\mathrm{up}}$ total = 2500 → per round = 50.0
- $N_{\mathrm{agg}}$: raw report line is 0. ECPFL selects `topk` residual blocks each round; each selected client uploads 2.0 blocks. The server aggregates one global ciphertext per selected block, so broadcast aggregated blocks per round = 2.0.
- Up volume total = 797.00 MB → per round = 15.9 MB
- Effective Down volume total = 17.28 MB → per round = 0.3 MB
- CT Upload Time total = 78.62 s (used as 50-round total in table)
- CT Download Time total = 2.31 s (used as 50-round total in table)
- Total Simulated Time = 129.89 s (used as 50-round TT in the table)

### FMNIST

#### FedAvg+CKKS (cnn_fmnist)
- Raw report path: `accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_015145_fashion_mnist`
- Final accuracy: 90.96%
- $N_{\mathrm{up}}$ total = 12500 → per round = 250.0
- $N_{\mathrm{agg}}$ total = 1000 → raw per round = 20.0; detected logging factor = 2, so unique aggregated batches per round = 10.0
- $N_{\mathrm{agg}}$ total = 1000 → per round = 20.0
- Up volume total = 3985.09 MB → per round = 79.7 MB
- Down volume total = 3985.09 MB → per round = 79.7 MB
- CT Upload Time total = 244.59 s (used as 50-round total in table)
- CT Download Time total = 165.96 s (used as 50-round total in table)
- Total Simulated Time = 285.43 s (used as 50-round TT in the table)

#### FedPHE (cnn_fmnist)
- Raw report path: `accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_125524_fashion_mnist`
- Final accuracy: 79.02%
- $N_{\mathrm{up}}$ total = 1250 → per round = 25.0
- $N_{\mathrm{agg}}$ total = 100 → raw per round = 2.0; detected logging factor = 2, so unique aggregated batches per round = 1.0
- $N_{\mathrm{agg}}$ total = 100 → per round = 2.0
- Up volume total = 398.55 MB → per round = 8.0 MB
- Down volume total = 3645.94 MB → per round = 72.9 MB
- CT Upload Time total = 24.46 s (used as 50-round total in table)
- CT Download Time total = 151.84 s (used as 50-round total in table)
- Total Simulated Time = 179.43 s (used as 50-round TT in the table)

#### ESAFL (cnn_fmnist)
- Raw report path: `accuracy_baseline/esafl/result_fix_pro/experiment_20260622_111118_fashion_mnist`
- Final accuracy: 89.51%
- $N_{\mathrm{up}}$ total = 6250 → per round = 125.0
- $N_{\mathrm{agg}}$ total = 500 → raw per round = 10.0; detected logging factor = 2, so unique aggregated batches per round = 5.0
- $N_{\mathrm{agg}}$ total = 500 → per round = 10.0
- Up volume total = 1992.65 MB → per round = 39.9 MB
- Down volume total = 1992.65 MB → per round = 39.9 MB
- CT Upload Time total = 122.30 s (used as 50-round total in table)
- CT Download Time total = 82.99 s (used as 50-round total in table)
- Total Simulated Time = 244.43 s (used as 50-round TT in the table)

#### MASER (cnn_fmnist)
- Raw report path: `accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist`
- Final accuracy: 90.66%
- $N_{\mathrm{up}}$ total = 7475 → per round = 149.5
- $N_{\mathrm{agg}}$ total = 598 → raw per round = 12.0; detected logging factor = 2, so unique aggregated batches per round = 6.0
- $N_{\mathrm{agg}}$ total = 598 → per round = 12.0
- Up volume total = 4766.15 MB → per round = 95.3 MB
- Down volume total = 2573.86 MB → per round = 51.5 MB
- CT Upload Time total = 292.54 s (used as 50-round total in table)
- CT Download Time total = 107.19 s (used as 50-round total in table)
- Total Simulated Time = 427.77 s (used as 50-round TT in the table)

#### ECPFL-RK (cnn_fmnist)
- Raw report path: `accuracy_baseline/ours/result/fashion_mnist_rk`
- Final accuracy: 87.31%
- $N_{\mathrm{up}}$ total = 3750 → per round = 75.0
- $N_{\mathrm{agg}}$: raw report line is 0. ECPFL selects `topk` residual blocks each round; each selected client uploads 3.0 blocks. The server aggregates one global ciphertext per selected block, so broadcast aggregated blocks per round = 3.0.
- Up volume total = 1195.51 MB → per round = 23.9 MB
- Effective Down volume total = 21.55 MB → per round = 0.4 MB
- CT Upload Time total = 52.66 s (used as 50-round total in table)
- CT Download Time total = 0.81 s (used as 50-round total in table)
- Total Simulated Time = 95.85 s (used as 50-round TT in the table)

### CIFAR-10

#### FedAvg+CKKS (resnet20)
- Raw report path: `accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260616_104710_cifar10`
- Final accuracy: 77.56%
- $N_{\mathrm{up}}$ total = 83750 → per round = 1675.0
- $N_{\mathrm{agg}}$ total = 6700 → raw per round = 134.0; detected logging factor = 2, so unique aggregated batches per round = 67.0
- $N_{\mathrm{agg}}$ total = 6700 → per round = 134.0
- Up volume total = 26699.46 MB → per round = 534.0 MB
- Down volume total = 26699.46 MB → per round = 534.0 MB
- CT Upload Time total = 1638.71 s (used as 50-round total in table)
- CT Download Time total = 1111.93 s (used as 50-round total in table)
- Total Simulated Time = 1756.32 s (used as 50-round TT in the table)

#### FedPHE (resnet20)
- Raw report path: `accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_131120_cifar10`
- Final accuracy: 75.77%
- $N_{\mathrm{up}}$ total = 42500 → per round = 850.0
- $N_{\mathrm{agg}}$ total = 3400 → raw per round = 68.0; detected logging factor = 2, so unique aggregated batches per round = 34.0
- $N_{\mathrm{agg}}$ total = 3400 → per round = 68.0
- Up volume total = 13548.73 MB → per round = 271.0 MB
- Down volume total = 18960.94 MB → per round = 379.2 MB
- CT Upload Time total = 831.57 s (used as 50-round total in table)
- CT Download Time total = 789.65 s (used as 50-round total in table)
- Total Simulated Time = 1221.47 s (used as 50-round TT in the table)

#### ESAFL (resnet20)
- Raw report path: `accuracy_baseline/esafl/result_fix_pro/experiment_20260622_114557_cifar10`
- Final accuracy: 81.91%
- $N_{\mathrm{up}}$ total = 42500 → per round = 850.0
- $N_{\mathrm{agg}}$ total = 3400 → raw per round = 68.0; detected logging factor = 2, so unique aggregated batches per round = 34.0
- $N_{\mathrm{agg}}$ total = 3400 → per round = 68.0
- Up volume total = 13549.24 MB → per round = 271.0 MB
- Down volume total = 13549.24 MB → per round = 271.0 MB
- CT Upload Time total = 831.60 s (used as 50-round total in table)
- CT Download Time total = 564.28 s (used as 50-round total in table)
- Total Simulated Time = 1402.62 s (used as 50-round TT in the table)

#### MASER (resnet20)
- Raw report path: `accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10`
- Final accuracy: 80.64%
- $N_{\mathrm{up}}$ total = 42450 → per round = 849.0
- $N_{\mathrm{agg}}$ total = 3396 → raw per round = 67.9; detected logging factor = 2, so unique aggregated batches per round = 34.0
- $N_{\mathrm{agg}}$ total = 3396 → per round = 67.9
- Up volume total = 27066.40 MB → per round = 541.3 MB
- Down volume total = 14839.93 MB → per round = 296.8 MB
- CT Upload Time total = 1661.20 s (used as 50-round total in table)
- CT Download Time total = 618.02 s (used as 50-round total in table)
- Total Simulated Time = 1927.93 s (used as 50-round TT in the table)

#### ECPFL-RK (resnet20)
- Raw report path: `accuracy_baseline/ours/result/cifar10_rk`
- Final accuracy: 76.51%
- $N_{\mathrm{up}}$ total = 58750 → per round = 1175.0
- $N_{\mathrm{agg}}$: raw report line is 0. ECPFL selects `topk` residual blocks each round; each selected client uploads 47.0 blocks. The server aggregates one global ciphertext per selected block, so broadcast aggregated blocks per round = 47.0.
- Up volume total = 18729.71 MB → per round = 374.6 MB
- Effective Down volume total = 382.91 MB → per round = 7.7 MB
- CT Upload Time total = 1355.66 s (used as 50-round total in table)
- CT Download Time total = 35.49 s (used as 50-round total in table)
- Total Simulated Time = 1441.36 s (used as 50-round TT in the table)

### SVHN

#### FedAvg+CKKS (resnet32)
- Raw report path: `accuracy_baseline/fedavg+ckks/result_fix_pro/experiment_20260629_140648_svhn`
- Final accuracy: 95.24%
- $N_{\mathrm{up}}$ total = 143750 → per round = 2875.0
- $N_{\mathrm{agg}}$ total = 11500 → raw per round = 230.0; detected logging factor = 2, so unique aggregated batches per round = 115.0
- $N_{\mathrm{agg}}$ total = 11500 → per round = 230.0
- Up volume total = 45828.08 MB → per round = 916.6 MB
- Down volume total = 32536.97 MB → per round = 650.7 MB
- CT Upload Time total = 2522.70 s (used as 50-round total in table)
- CT Download Time total = 1137.73 s (used as 50-round total in table)
- Total Simulated Time = 3141.61 s (used as 50-round TT in the table)

#### FedPHE (resnet32)
- Raw report path: `accuracy_baseline/fedphe/result_fix_pro/experiment_20260616_134815_svhn`
- Final accuracy: 94.44%
- $N_{\mathrm{up}}$ total = 72500 → per round = 1450.0
- $N_{\mathrm{agg}}$ total = 5800 → raw per round = 116.0; detected logging factor = 2, so unique aggregated batches per round = 58.0
- $N_{\mathrm{agg}}$ total = 5800 → per round = 116.0
- Up volume total = 23112.74 MB → per round = 462.3 MB
- Down volume total = 32567.46 MB → per round = 651.3 MB
- CT Upload Time total = 1418.58 s (used as 50-round total in table)
- CT Download Time total = 1356.31 s (used as 50-round total in table)
- Total Simulated Time = 2445.11 s (used as 50-round TT in the table)

#### ESAFL (resnet32)
- Raw report path: `accuracy_baseline/esafl/result_fix_pro/experiment_20260622_130213_svhn`
- Final accuracy: 95.74%
- $N_{\mathrm{up}}$ total = 72500 → per round = 1450.0
- $N_{\mathrm{agg}}$ total = 5800 → raw per round = 116.0; detected logging factor = 2, so unique aggregated batches per round = 58.0
- $N_{\mathrm{agg}}$ total = 5800 → per round = 116.0
- Up volume total = 23113.26 MB → per round = 462.3 MB
- Down volume total = 23113.26 MB → per round = 462.3 MB
- CT Upload Time total = 1418.61 s (used as 50-round total in table)
- CT Download Time total = 962.58 s (used as 50-round total in table)
- Total Simulated Time = 2363.50 s (used as 50-round TT in the table)

#### MASER (resnet32)
- Raw report path: `accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn`
- Final accuracy: 95.82%
- $N_{\mathrm{up}}$ total = 73700 → per round = 1474.0
- $N_{\mathrm{agg}}$ total = 5896 → raw per round = 117.9; detected logging factor = 2, so unique aggregated batches per round = 59.0
- $N_{\mathrm{agg}}$ total = 5896 → per round = 117.9
- Up volume total = 46991.57 MB → per round = 939.8 MB
- Down volume total = 25733.91 MB → per round = 514.7 MB
- CT Upload Time total = 2884.12 s (used as 50-round total in table)
- CT Download Time total = 1071.71 s (used as 50-round total in table)
- Total Simulated Time = 3308.35 s (used as 50-round TT in the table)

#### ECPFL-RK (resnet32)
- Raw report path: `accuracy_baseline/ours/result/svhn_rk`
- Final accuracy: 95.20%
- $N_{\mathrm{up}}$ total = 100000 → per round = 2000.0
- $N_{\mathrm{agg}}$: raw report line is 0. ECPFL selects `topk` residual blocks each round; each selected client uploads 80.0 blocks. The server aggregates one global ciphertext per selected block, so broadcast aggregated blocks per round = 80.0.
- Up volume total = 31880.43 MB → per round = 637.6 MB
- Effective Down volume total = 555.29 MB → per round = 11.1 MB
- CT Upload Time total = 771.91 s (used as 50-round total in table)
- CT Download Time total = 20.26 s (used as 50-round total in table)
- Total Simulated Time = 923.17 s (used as 50-round TT in the table)

## Known inconsistencies / sanity checks

1. **SVHN model consistency**: All SVHN methods now use `resnet32`. The new FedAvg+CKKS SVHN report (`experiment_20260629_140648_svhn`) supersedes the older `cnn` report (`experiment_20260616_115455_svhn`). All baseline reports currently exhibit double-logging of `aggregated_ciphertexts` (100 entries for 50 rounds), so $N_{\mathrm{agg}}$ is divided by 2.
2. **MASER download volume**: MASER reports a smaller downstream volume than FedAvg+CKKS because it broadcasts a plaintext model after server-side decryption; the bulk of its overhead is in server-side multi-key CKKS partial-decryption and is captured in TT, not in the comm-volume columns.
3. **ECPFL-RK latency split**: The rerun reports contain direct `CT Upload Time` and `CT Download Time` lines, so UT and DT are taken directly from the report. TT is the report's `Total Simulated Time`. Older ECPFL reports without separate CT times estimated upload/download latencies by proportionally splitting `Total Simulated Comm Time` according to upload and effective-download volumes.
4. **Time column scale**: The `Time (s)` columns (UT/DT/TT) are reported as 50-round totals, while Batches and Communication (MB) remain per-round averages. This avoids rounding very small per-round download times (e.g., ECPFL-RK on MNIST/FMNIST) to 0.0.
5. **Sparse vs non-sparse upload counts**: On MNIST/FMNIST, FedAvg+CKKS has the largest $N_{\mathrm{up}}$ (no sparsification), while FedPHE/ECPFL-RK have the smallest (most aggressive sparsification/packing). On CIFAR-10/SVHN the ranking is FedAvg+CKKS > ECPFL-RK > FedPHE/ESAFL/MASER, because ECPFL-RK uses topk=0.7 while the other sparse baselines use roughly 0.5 sparsity. ECPFL-RK's $N_{\mathrm{agg}}$ equals the number of selected residual blocks (2/3/47/80), not 1.
