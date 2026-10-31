import json
import re

# 真实数据路径
paths = {
    "FedAvg+CKKS": {
        "MNIST": "accuracy_baseline/fedavg+ckks/result/experiment_20260610_141045_mnist/metrics.json",
        "FMNIST": "accuracy_baseline/fedavg+ckks/result/experiment_20260610_145058_fmnist/metrics.json",
        "CIFAR-10": "accuracy_baseline/fedavg+ckks/result/experiment_20260610_162015_cifar10/metrics.json",
        "SVHN": "accuracy_baseline/fedavg+ckks/result/experiment_20260610_171227_svhn/metrics.json",
    },
    "ESAFL": {
        "MNIST": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_104429_mnist/metrics.json",
        "FMNIST": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_111118_fashion_mnist_alpha_1/metrics.json",
        "CIFAR-10": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_114557_cifar10_alpha_1/metrics.json",
        "SVHN": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_130213_svhn/metrics.json",
    },
}

# 提取 test_acc 数据
real_data = {}
for method, datasets in paths.items():
    real_data[method] = {}
    for dataset, path in datasets.items():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                test_acc = data.get('test_acc', [])
                if test_acc:
                    # 转换为 0-1 范围（如果已经是 0-1 则保持不变）
                    if max(test_acc) > 1:
                        test_acc = [x / 100.0 for x in test_acc]
                    real_data[method][dataset] = test_acc[:50]  # 取前50轮
                    print(f"{method} - {dataset}: {len(test_acc)} rounds, final={test_acc[-1]:.4f}")
                else:
                    print(f"Warning: No test_acc in {path}")
        except Exception as e:
            print(f"Error reading {path}: {e}")

# 读取 plot_compare_methods.py
with open('tools/plot_experiment/plot_compare/script/plot_compare_methods.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换数据
for method in ["FedAvg+CKKS", "ESAFL"]:
    for dataset in ["MNIST", "FMNIST", "CIFAR-10", "SVHN"]:
        if method in real_data and dataset in real_data[method]:
            data_list = real_data[method][dataset]
            # 格式化数据
            data_str = "[" + ", ".join([f"{x:.4f}" for x in data_list]) + "]"
            
            # 构建正则表达式模式
            # 匹配: "METHOD": [数字, 数字, ...]
            pattern = rf'("{re.escape(method)}":\s*\[[\d\.,\s]+\])'
            
            # 查找并替换
            match = re.search(pattern, content)
            if match:
                old_str = match.group(1)
                new_str = f'"{method}": {data_str}'
                content = content.replace(old_str, new_str)
                print(f"Replaced {method} - {dataset}")
            else:
                print(f"Pattern not found for {method} - {dataset}")

# 写回文件
with open('tools/plot_experiment/plot_compare/script/plot_compare_methods.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done!")
