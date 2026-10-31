# Adaptive Voting 跨数据集 50 轮对比

| Dataset | Strategy | Final Acc (%) | Total Time (s) | Comm (MB) | Avg Expansion |
|---------|----------|---------------|----------------|-----------|---------------|
| fashion_mnist | baseline | 84.43 | 183.61 | 1217.04 | 6.27x |
| fashion_mnist | cosine | 87.68 | 181.27 | 1455.94 | 7.44x |
| fashion_mnist | accuracy | 82.82 | 136.68 | 555.53 | 2.80x |
| fashion_mnist | consensus | 85.76 | 151.76 | 1201.13 | 6.18x |
| mnist | baseline | — | — | — | — |
| mnist | cosine | — | — | — | — |
| mnist | accuracy | — | — | — | — |
| mnist | consensus | — | — | — | — |
| cifar10 | baseline | — | — | — | — |
| cifar10 | cosine | — | — | — | — |
| cifar10 | accuracy | — | — | — | — |
| cifar10 | consensus | — | — | — | — |
| svhn | baseline | — | — | — | — |
| svhn | cosine | — | — | — | — |
| svhn | accuracy | — | — | — | — |
| svhn | consensus | — | — | — | — |

## Relative to dataset baseline (topk)

| Dataset | Strategy | Δ Acc (pp) | Time Ratio | Comm Ratio |
|---------|----------|------------|------------|------------|
| fashion_mnist | cosine | +3.25 | 0.99x | 1.20x |
| fashion_mnist | accuracy | -1.61 | 0.74x | 0.46x |
| fashion_mnist | consensus | +1.33 | 0.83x | 0.99x |
