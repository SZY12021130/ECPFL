# Compare Analysis Summary: Merged vs CRTStack × Voting Modes

## Experiment Settings
- **Dataset**: MNIST
- **Model**: LeNet
- **Rounds**: 30
- **Clients**: 100
- **Sampling Rate**: 0.3
- **Overcommitment (OC)**: 1.3
- **Strategy**: Sticky Sampling

## Results Summary

| Config | Final Acc | Final Loss | Total Comm (MB) | Upload (MB) | Download (MB) | CT Count | Avg Round (s) | Time (s) |
|--------|-----------|------------|-----------------|-------------|---------------|----------|---------------|----------|
| Merged None | 98.05% | 0.0598 | 5409.36 | 3156.16 | 2253.20 | 9900 | 12.62 | 0.0 |
| Merged Union | 97.79% | 0.0653 | 4638.23 | 2362.33 | 2275.90 | 7410 | 11.83 | 0.0 |
| Merged Threshold | 97.37% | 0.0783 | 3619.08 | 1300.73 | 2318.35 | 4080 | 10.91 | 0.0 |
| Crtstack None | 97.93% | 0.0608 | 1721.56 | 860.75 | 860.81 | 2700 | 11.71 | 0.0 |
| Crtstack Union | 97.38% | 0.0789 | 1501.58 | 640.79 | 860.78 | 2010 | 11.74 | 382.7 |
| Crtstack Threshold | 95.68% | 0.1333 | 1061.64 | 200.84 | 860.80 | 630 | 16.40 | 520.6 |

## Key Observations

1. **Best Accuracy**: Merged None with 98.05%
2. **Lowest Communication**: Crtstack Threshold with 1061.64 MB
3. **CRTStack Communication Savings**: 68.6% (avg across voting modes)
4. **CRTStack Accuracy Impact**: -0.74pp (avg across voting modes)

## Note
This is an ESAFL simulation experiment. The server-side decrypt-re-encrypt overhead is not counted in the metrics. The communication and accuracy data reflect the actual protocol behavior.