# 实验汇总分析与最平衡结果

> 涵盖目录：`accuracy_client_selection`、`accuracy_threshold_v2`、`accuracy_topk_v2`、`accuracy_niid`、`accuracy_noprefetch`、`accuracy`


## 分析维度

- **准确率**：最终第 50 轮测试准确率
- **通信量**：累计总通信量（上行 + 下行，单位 MB）
- **通信时间**：累计模拟通信时间（单位 秒）
- **平衡得分**：归一化后加权 `0.5×准确率 − 0.25×通信量 − 0.25×通信时间`，越高越平衡

## MNIST

### 全部实验汇总

| 实验目录 | 方法 | 准确率 | 总通信 (MB) | 通信时间 (s) | 平衡得分 |
|----------|------|:---:|:---:|:---:|:---:|
| accuracy | baseline | 98.82% | 3313.42 | 112.82 | 0.8452 |
| accuracy | baseline | 98.84% | 3577.62 | 116.64 | 0.8409 |
| accuracy | baseline | 98.82% | 3232.58 | 127.09 | 0.8377 |
| accuracy | baseline | 98.93% | 4449.63 | 141.89 | 0.8270 |
| accuracy_niid | niid | 98.91% | 4183.35 | 149.90 | 0.8227 |
| accuracy_niid | niid | 98.93% | 4204.94 | 163.73 | 0.8199 |
| accuracy | baseline | 98.81% | 3784.87 | 123.53 | 0.8155 |
| accuracy | baseline | 98.83% | 4239.19 | 127.70 | 0.8037 |
| accuracy | baseline | 98.85% | 4414.53 | 140.30 | 0.7962 |
| accuracy | baseline | 98.83% | 4342.78 | 135.85 | 0.7938 |
| accuracy | baseline | 98.81% | 4457.59 | 142.81 | 0.7760 |
| accuracy_niid | niid | 98.82% | 4183.37 | 167.60 | 0.7720 |
| accuracy | baseline | 98.79% | 4457.63 | 139.70 | 0.7700 |
| accuracy | baseline | 98.77% | 4422.47 | 139.38 | 0.7632 |
| accuracy_threshold_v2 | threshold_0.7 | 98.55% | 1540.79 | 193.69 | 0.7389 |
| accuracy_client_selection | sticky | 98.32% | 814.28 | 106.59 | 0.7350 |
| accuracy_client_selection | poc | 98.28% | 808.68 | 109.52 | 0.7163 |
| accuracy_niid | niid | 98.70% | 4404.04 | 166.66 | 0.7145 |
| accuracy_client_selection | oort | 98.25% | 808.22 | 103.48 | 0.7083 |
| accuracy_niid | niid | 98.67% | 4350.79 | 162.52 | 0.7070 |
| accuracy_threshold_v2 | threshold_0.5 | 98.65% | 2249.22 | 257.61 | 0.7066 |
| accuracy_topk_v2 | topk_0.3 | 98.49% | 1628.57 | 201.49 | 0.7048 |
| accuracy_topk_v2 | topk_0.5 | 98.66% | 2442.64 | 270.75 | 0.6937 |
| accuracy_client_selection | haccs | 98.25% | 812.04 | 129.96 | 0.6885 |
| accuracy_topk_v2 | topk_0.7 | 98.82% | 3252.88 | 339.32 | 0.6792 |
| accuracy_threshold_v2 | threshold_0.3 | 98.80% | 3166.23 | 340.10 | 0.6735 |
| accuracy_threshold_v2 | threshold_0.9 | 98.21% | 861.54 | 130.65 | 0.6695 |
| accuracy_client_selection | sketch_clustering | 98.15% | 812.93 | 108.87 | 0.6625 |
| accuracy_topk_v2 | topk_0.1 | 98.15% | 814.28 | 120.58 | 0.6537 |
| accuracy_client_selection | random | 98.12% | 811.13 | 103.95 | 0.6537 |
| accuracy_client_selection | tifl | 98.13% | 814.06 | 122.61 | 0.6439 |
| accuracy_topk_v2 | topk_0.9 | 98.84% | 4063.16 | 413.60 | 0.6020 |
| accuracy_noprefetch | noprefetch | 98.87% | 6255.44 | 340.51 | 0.5869 |
| accuracy_threshold_v2 | threshold_0.1 | 98.80% | 4152.93 | 422.46 | 0.5754 |
| accuracy_topk_v2 | union | 98.83% | 4312.78 | 439.83 | 0.5690 |
| accuracy_noprefetch | noprefetch | 98.91% | 6815.03 | 393.18 | 0.5435 |
| accuracy_noprefetch | noprefetch | 98.95% | 7364.97 | 422.98 | 0.5174 |
| accuracy_noprefetch | noprefetch | 98.95% | 7418.43 | 420.75 | 0.5171 |
| accuracy_noprefetch | noprefetch | 98.92% | 7495.72 | 402.79 | 0.5150 |
| accuracy_noprefetch | noprefetch | 98.88% | 7495.79 | 415.81 | 0.4887 |
| accuracy_noprefetch | noprefetch | 98.88% | 7495.78 | 434.08 | 0.4751 |
| accuracy_niid | niid | 97.75% | 4444.03 | 133.66 | 0.3416 |

### 最平衡的 Top-3 配置

| 排名 | 方法 | 准确率 | 总通信 (MB) | 通信时间 (s) | 平衡得分 |
|------|------|:---:|:---:|:---:|:---:|
| 1 | baseline | 98.82% | 3313.42 | 112.82 | 0.8452 |
| 2 | baseline | 98.84% | 3577.62 | 116.64 | 0.8409 |
| 3 | baseline | 98.82% | 3232.58 | 127.09 | 0.8377 |

## Fashion-MNIST

### 全部实验汇总

| 实验目录 | 方法 | 准确率 | 总通信 (MB) | 通信时间 (s) | 平衡得分 |
|----------|------|:---:|:---:|:---:|:---:|
| accuracy | baseline | 81.44% | 741.33 | 51.31 | 0.9207 |
| accuracy_threshold_v2 | threshold_0.9 | 84.59% | 867.95 | 138.80 | 0.8764 |
| accuracy | baseline | 90.09% | 2697.13 | 103.92 | 0.8673 |
| accuracy_client_selection | tifl | 85.82% | 1220.19 | 145.32 | 0.8666 |
| accuracy_client_selection | oort | 85.83% | 1212.34 | 146.66 | 0.8661 |
| accuracy_client_selection | random | 85.51% | 1217.49 | 143.45 | 0.8659 |
| accuracy_topk_v2 | topk_0.3 | 86.16% | 1220.41 | 150.73 | 0.8652 |
| accuracy_client_selection | sticky | 85.80% | 1220.43 | 150.93 | 0.8626 |
| accuracy_client_selection | poc | 85.51% | 1213.00 | 157.82 | 0.8560 |
| accuracy_client_selection | sketch_clustering | 85.49% | 1218.84 | 159.54 | 0.8545 |
| accuracy_client_selection | haccs | 85.54% | 1216.15 | 160.20 | 0.8545 |
| accuracy_niid | niid | 90.23% | 2968.42 | 114.72 | 0.8502 |
| accuracy | baseline | 90.28% | 2952.54 | 137.09 | 0.8355 |
| accuracy_niid | niid | 90.15% | 3103.97 | 130.33 | 0.8334 |
| accuracy_threshold_v2 | threshold_0.7 | 86.35% | 1437.30 | 186.83 | 0.8328 |
| accuracy_niid | niid | 89.15% | 3295.23 | 124.58 | 0.8231 |
| accuracy_niid | niid | 90.16% | 3449.00 | 141.30 | 0.8124 |
| accuracy_niid | niid | 79.07% | 756.82 | 216.87 | 0.7882 |
| accuracy_topk_v2 | topk_0.5 | 87.99% | 2036.27 | 237.48 | 0.7854 |
| accuracy_niid | niid | 89.44% | 3887.36 | 151.38 | 0.7833 |
| accuracy | baseline | 90.67% | 4052.39 | 157.70 | 0.7809 |
| accuracy | baseline | 90.74% | 4052.39 | 158.72 | 0.7807 |
| accuracy | baseline | 90.72% | 4052.39 | 160.52 | 0.7793 |
| accuracy_threshold_v2 | threshold_0.5 | 88.03% | 2034.48 | 247.51 | 0.7787 |
| accuracy_threshold_v2 | threshold_0.3 | 88.74% | 2202.75 | 259.81 | 0.7685 |
| accuracy_threshold_v2 | threshold_0.1 | 90.01% | 2633.13 | 302.05 | 0.7310 |
| accuracy_topk_v2 | topk_0.7 | 89.86% | 2846.73 | 310.93 | 0.7154 |
| accuracy_topk_v2 | union | 90.20% | 2929.58 | 323.18 | 0.7060 |
| accuracy_noprefetch | noprefetch | 81.78% | 4378.62 | 256.97 | 0.6376 |
| accuracy_topk_v2 | topk_0.9 | 90.25% | 3656.98 | 382.19 | 0.6367 |
| accuracy_noprefetch | noprefetch | 90.32% | 5488.76 | 331.99 | 0.6008 |
| accuracy_noprefetch | noprefetch | 90.39% | 5669.03 | 339.41 | 0.5891 |
| accuracy_noprefetch | noprefetch | 90.96% | 6814.32 | 407.45 | 0.5008 |
| accuracy_noprefetch | noprefetch | 90.97% | 6814.37 | 408.51 | 0.5001 |
| accuracy_noprefetch | noprefetch | 91.04% | 6814.35 | 409.41 | 0.5000 |
| accuracy_noprefetch | noprefetch | 91.02% | 6814.35 | 409.37 | 0.4999 |
| accuracy_topk_v2 | topk_0.1 | 18.53% | 406.13 | 101.04 | 0.4653 |

### 最平衡的 Top-3 配置

| 排名 | 方法 | 准确率 | 总通信 (MB) | 通信时间 (s) | 平衡得分 |
|------|------|:---:|:---:|:---:|:---:|
| 1 | baseline | 81.44% | 741.33 | 51.31 | 0.9207 |
| 2 | threshold_0.9 | 84.59% | 867.95 | 138.80 | 0.8764 |
| 3 | baseline | 90.09% | 2697.13 | 103.92 | 0.8673 |

## CIFAR-10

### 全部实验汇总

| 实验目录 | 方法 | 准确率 | 总通信 (MB) | 通信时间 (s) | 平衡得分 |
|----------|------|:---:|:---:|:---:|:---:|
| accuracy_client_selection | sketch_clustering | 77.03% | 19110.74 | 1433.61 | 0.8623 |
| accuracy_client_selection | tifl | 76.94% | 19102.69 | 1420.90 | 0.8616 |
| accuracy_client_selection | oort | 76.87% | 18993.41 | 1440.05 | 0.8609 |
| accuracy_threshold_v2 | threshold_0.5 | 72.92% | 12935.36 | 1021.45 | 0.8594 |
| accuracy_topk_v2 | topk_0.5 | 73.43% | 13832.89 | 1062.38 | 0.8593 |
| accuracy_client_selection | random | 76.61% | 19069.33 | 1425.60 | 0.8577 |
| accuracy_threshold_v2 | threshold_0.1 | 76.67% | 19207.67 | 1464.31 | 0.8566 |
| accuracy_threshold_v2 | threshold_0.3 | 74.99% | 16530.19 | 1294.87 | 0.8563 |
| accuracy_client_selection | haccs | 76.37% | 19057.42 | 1435.93 | 0.8546 |
| accuracy_topk_v2 | topk_0.7 | 76.24% | 19112.57 | 1449.47 | 0.8524 |
| accuracy_client_selection | sticky | 75.95% | 19114.15 | 1423.24 | 0.8495 |
| accuracy_topk_v2 | union | 76.77% | 20513.82 | 1564.87 | 0.8476 |
| accuracy_client_selection | poc | 75.71% | 19003.98 | 1429.78 | 0.8471 |
| accuracy_niid | niid | 77.36% | 26581.86 | 751.75 | 0.8403 |
| accuracy | baseline | 77.45% | 27103.22 | 757.20 | 0.8382 |
| accuracy | baseline | 77.48% | 27150.95 | 769.36 | 0.8379 |
| accuracy | baseline | 77.23% | 26768.40 | 743.67 | 0.8378 |
| accuracy_topk_v2 | topk_0.3 | 67.92% | 8550.63 | 699.55 | 0.8330 |
| accuracy | baseline | 76.86% | 27150.96 | 768.58 | 0.8305 |
| accuracy_topk_v2 | topk_0.9 | 77.80% | 24785.16 | 1853.72 | 0.8276 |
| accuracy_threshold_v2 | threshold_0.7 | 65.58% | 7777.90 | 689.17 | 0.8095 |
| accuracy_niid | niid | 65.52% | 11611.69 | 371.60 | 0.7946 |
| accuracy_niid | niid | 65.64% | 15044.40 | 429.02 | 0.7745 |
| accuracy_niid | niid | 63.78% | 12470.06 | 387.70 | 0.7682 |
| accuracy_noprefetch | noprefetch | 78.14% | 45656.19 | 2218.70 | 0.7004 |
| accuracy_noprefetch | noprefetch | 78.07% | 45602.62 | 2217.33 | 0.6999 |
| accuracy_noprefetch | noprefetch | 77.96% | 45656.12 | 2201.64 | 0.6987 |
| accuracy_noprefetch | noprefetch | 77.36% | 44765.73 | 2172.26 | 0.6974 |
| accuracy_threshold_v2 | threshold_0.9 | 53.08% | 4294.28 | 428.58 | 0.6858 |
| accuracy_niid | niid | 76.80% | 26440.03 | 9833.95 | 0.6000 |
| accuracy_niid | niid | 75.93% | 26700.34 | 9806.81 | 0.5887 |
| accuracy_niid | niid | 75.18% | 26487.95 | 9877.22 | 0.5791 |
| accuracy_niid | niid | 74.84% | 26758.72 | 9988.75 | 0.5705 |
| accuracy_niid | niid | 71.91% | 25307.66 | 9751.48 | 0.5498 |
| accuracy_niid | niid | 50.73% | 26393.88 | 759.13 | 0.5199 |
| accuracy_topk_v2 | topk_0.1 | 36.70% | 2844.95 | 297.54 | 0.5000 |
| accuracy_niid | niid | 46.43% | 26181.12 | 9869.78 | 0.2342 |

### 最平衡的 Top-3 配置

| 排名 | 方法 | 准确率 | 总通信 (MB) | 通信时间 (s) | 平衡得分 |
|------|------|:---:|:---:|:---:|:---:|
| 1 | sketch_clustering | 77.03% | 19110.74 | 1433.61 | 0.8623 |
| 2 | tifl | 76.94% | 19102.69 | 1420.90 | 0.8616 |
| 3 | oort | 76.87% | 18993.41 | 1440.05 | 0.8609 |

## 关键结论

- **MNIST**：最平衡配置为 `baseline`（准确率 98.82%，通信 3313.42 MB，时间 112.82 s）
- **Fashion-MNIST**：最平衡配置为 `baseline`（准确率 81.44%，通信 741.33 MB，时间 51.31 s）
- **CIFAR-10**：最平衡配置为 `sketch_clustering`（准确率 77.03%，通信 19110.74 MB，时间 1433.61 s）
