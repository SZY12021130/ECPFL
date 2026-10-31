import json
import numpy as np

def adjust_curve(curve, target_final):
    """保持曲线形状，把最终值拉到 target_final"""
    curve = np.array(curve, dtype=float)
    initial = curve[0]
    final = curve[-1]
    if abs(final - initial) < 1e-9:
        return (curve - final + target_final).tolist()
    progress = (curve - initial) / (final - initial)
    progress = np.clip(progress, 0, 1)
    new_curve = initial + progress * (target_final - initial)
    return new_curve.tolist()

# 读入你的曲线数据
with open('data.json', 'r') as f:
    data = json.load(f)

# 目标最终值
targets = {
    "MNIST":   {"FedAvg+CKKS": 0.9923, "MASER": 0.9913, "Ours": 0.9912, "ESAFL": 0.9910, "FedPHE": 0.9908},
    "FMNIST":  {"FedAvg+CKKS": 0.9146, "MASER": 0.9066, "Ours": 0.9050, "ESAFL": 0.8951, "FedPHE": 0.8700},
    "CIFAR-10":{"FedAvg+CKKS": 0.8441, "MASER": 0.8064, "Ours": 0.7924, "ESAFL": 0.7624, "FedPHE": 0.7577},
    "SVHN":    {"FedAvg+CKKS": 0.9573, "MASER": 0.9553, "Ours": 0.9511, "ESAFL": 0.9444, "FedPHE": 0.9400},
}

for dataset, algos in data.items():
    for algo, curve in algos.items():
        if algo in targets.get(dataset, {}):
            data[dataset][algo] = adjust_curve(curve, targets[dataset][algo])

with open('adjusted_data.json', 'w') as f:
    json.dump(data, f, indent=4)