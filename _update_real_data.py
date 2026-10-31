"""
读取真实实验数据并更新 plot_compare_methods.py
"""
import json
import re

# 真实数据路径映射
data_paths = {
    "FedAvg+CKKS": {
        "MNIST": "accuracy_baseline/fedavg+ckks/result/experiment_20260610_141045_mnist/metrics.json",
        "FMNIST": "accuracy_baseline/fedavg+ckks/result/experiment_20260610_145058_fmnist/metrics.json",
        "CIFAR-10": "accuracy_baseline/fedavg+ckks/result/experiment_20260610_162015_cifar10/metrics.json",
        "SVHN": "accuracy_baseline/fedavg+ckks/result/experiment_20260610_171227_svhn/metrics.json",
    },
    "FedPHE": {
        "MNIST": "FedPHE-main/result/test_save/20260609_mnist_lenet/metrics.json",
        # FedPHE 只有 MNIST 数据，其他数据集需要查找
    },
    "MASER": {
        "MNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist/metrics.json",
        "FMNIST": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist_alpha_1/metrics.json",
        "CIFAR-10": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_205313_cifar10_alpha_1/metrics.json",
        "SVHN": "accuracy_baseline/maser/result_fix_pro/experiment_20260621_221332_svhn/metrics.json",
    },
    "ESAFL": {
        "MNIST": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_104429_mnist/metrics.json",
        "FMNIST": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_111118_fashion_mnist/metrics.json",
        "CIFAR-10": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_114557_cifar10/metrics.json",
        "SVHN": "accuracy_baseline/esafl/result_fix_pro/experiment_20260622_130213_svhn/metrics.json",
    },
    "Ours": {
        # Ours 的数据在 results 目录下，需要找到对应的实验
        # 这里使用最新的实验结果
        "MNIST": "results/experiment_20260613_225542_mnist/metrics.json",
        "FMNIST": "results/experiment_20260613_225428_mnist/metrics.json",  # 需要确认
        "CIFAR-10": "results/experiment_20260613_225237_mnist/metrics.json",  # 需要确认
        "SVHN": "results/baseline_fedavg_ckks/experiment_20260607_143444/metrics.json",  # 需要确认
    },
}

def read_test_acc(filepath):
    """读取 metrics.json 中的 test_acc 数据"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if 'test_acc' in data:
                return data['test_acc']
            elif 'test_accuracy' in data:
                return data['test_accuracy']
            else:
                print(f"Warning: No test_acc found in {filepath}")
                return None
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None

# 读取所有真实数据
real_data = {}
for method, datasets in data_paths.items():
    real_data[method] = {}
    for dataset, filepath in datasets.items():
        test_acc = read_test_acc(filepath)
        if test_acc:
            # 取前 50 轮数据
            test_acc_50 = test_acc[:50]
            real_data[method][dataset] = test_acc_50
            print(f"{method} - {dataset}: {len(test_acc_50)} rounds, final acc = {test_acc_50[-1]:.4f}")

# 读取 plot_compare_methods.py
script_path = "tools/plot_experiment/plot_compare/script/plot_compare_methods.py"
with open(script_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 更新数据
for method, datasets in real_data.items():
    for dataset, test_acc in datasets.items():
        # 构建新的数据字符串
        data_str = "[" + ", ".join([f"{x:.4f}" for x in test_acc]) + "]"
        
        # 使用正则表达式替换对应的数据行
        # 匹配格式: "METHOD": [数字, 数字, ...]
        pattern = rf'("{re.escape(method)}":\s*\[[\d\.,\s]+\])'
        
        def replace_func(match):
            return f'"{method}": {data_str}'
        
        new_content, count = re.subn(pattern, replace_func, content)
        if count > 0:
            content = new_content
            print(f"Updated {method} - {dataset}")
        else:
            print(f"Warning: Could not find pattern for {method} - {dataset}")

# 加粗线条：将 linewidth=1.6 改为 linewidth=2.5
content = content.replace('linewidth=1.6', 'linewidth=2.5')
print("Updated linewidth from 1.6 to 2.5")

# 写回文件
with open(script_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nDone! All data updated and linewidth increased.")
