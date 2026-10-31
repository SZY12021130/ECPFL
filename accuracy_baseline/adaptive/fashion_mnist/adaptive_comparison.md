# FMNIST 15-round Adaptive Voting Comparison

| Strategy | Rounds | Final Acc (%) | Total Time (s) | Comm (MB) | Avg Expansion |
|----------|--------|---------------|----------------|-----------|---------------|
| baseline (topk 0.3) | 15 | 84.30 | 56.94 | 380.20 | 6.27x |
| adaptive_cosine | 15 | 86.75 | 65.04 | 483.59 | 7.80x |
| adaptive_accuracy | 15 | 81.63 | 59.56 | 276.59 | 4.46x |
| adaptive_consensus | 15 | 84.29 | 60.56 | 372.24 | 6.13x |

## Relative to baseline (topk 0.3) (15-round baseline)

| Strategy | Δ Acc (pp) | Time Ratio | Comm Ratio |
|----------|------------|------------|------------|
| adaptive_cosine | +2.45 | 1.14x | 1.27x |
| adaptive_accuracy | -2.67 | 1.05x | 0.73x |
| adaptive_consensus | -0.01 | 1.06x | 0.98x |

# FMNIST 50-round Adaptive Voting Comparison

| Strategy | Rounds | Final Acc (%) | Total Time (s) | Comm (MB) | Avg Expansion |
|----------|--------|---------------|----------------|-----------|---------------|
| baseline (topk 0.3) | 50 | 84.43 | 183.61 | 1217.04 | 6.27x |
| adaptive_cosine | 50 | 87.68 | 181.27 | 1455.94 | 7.44x |
| adaptive_accuracy | 50 | 82.82 | 136.68 | 555.53 | 2.80x |
| adaptive_consensus | 50 | 85.76 | 151.76 | 1201.13 | 6.18x |

## Relative to baseline (topk 0.3) (50-round baseline)

| Strategy | Δ Acc (pp) | Time Ratio | Comm Ratio |
|----------|------------|------------|------------|
| adaptive_cosine | +3.25 | 0.99x | 1.20x |
| adaptive_accuracy | -1.61 | 0.74x | 0.46x |
| adaptive_consensus | +1.33 | 0.83x | 0.99x |

# Older 50-round Baseline (accuracy_baseline/ours)

| Strategy | Rounds | Final Acc (%) | Total Time (s) | Comm (MB) | Avg Expansion |
|----------|--------|---------------|----------------|-----------|---------------|
| ours (50r topk 0.3) | 50 | 86.14 | 2459.42 | 1217.05 | 6.27x |

# 15-round vs. 50-round Summary

| Strategy | 15r Acc (%) | 15r Comm (MB) | 50r Acc (%) | 50r Comm (MB) | Δ Acc (pp) | Comm Ratio (50r/15r) |
|----------|-------------|---------------|-------------|---------------|------------|----------------------|
| baseline (topk 0.3) | 84.30 | 380.20 | 84.43 | 1217.04 | +0.13 | 3.20x |
| adaptive_cosine | 86.75 | 483.59 | 87.68 | 1455.94 | +0.93 | 3.01x |
| adaptive_accuracy | 81.63 | 276.59 | 82.82 | 555.53 | +1.19 | 2.01x |
| adaptive_consensus | 84.29 | 372.24 | 85.76 | 1201.13 | +1.47 | 3.23x |
