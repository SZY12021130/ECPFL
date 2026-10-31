import torch
import math
import sys
sys.path.insert(0, 'ckks_fed')
from models import create_model

SLOT_COUNT = 4096
# 从ResNet20实验数据估算：67 batch = 19.45 MB
BYTES_PER_BATCH = 19.45 * 1024 * 1024 / 67  # ≈ 290 KB/batch
KB_PER_BATCH = BYTES_PER_BATCH / 1024  # KB 单位

test_cases = [
    ('mlp', 1, 28, 10, 'MNIST'),
    ('cnn', 1, 28, 10, 'MNIST'),
    ('cnn', 3, 32, 10, 'CIFAR-10'),
    ('lenet', 1, 28, 10, 'MNIST'),
    ('lenet', 3, 32, 10, 'CIFAR-10'),
    ('deepcnn', 1, 28, 10, 'MNIST'),
    ('deepcnn', 3, 32, 10, 'CIFAR-10'),
    ('vggnobn', 1, 28, 10, 'MNIST'),
    ('vggnobn', 3, 32, 10, 'CIFAR-10'),
    ('mobilenetv2', 3, 32, 10, 'CIFAR-10'),
    ('densenet', 3, 32, 10, 'CIFAR-10'),
    ('resnet18', 3, 32, 10, 'CIFAR-10'),
    ('cnn_cifar', 3, 32, 10, 'CIFAR-10'),
    ('cnn_fmnist', 1, 28, 10, 'Fashion-MNIST'),
    ('resnet20', 3, 32, 10, 'CIFAR-10'),
    ('resnet32', 3, 32, 10, 'CIFAR-10'),
]

results = []
for name, channels, size, classes, dataset in test_cases:
    dataset_key = dataset.lower().replace('-', '_')
    dummy_cfg = {
        'data': {'dataset': dataset_key, 'num_classes': classes},
        'model': {'dropout': 0.2, 'hidden_dims': [256, 128], 'width_mult': 1.0, 'deepcnn_width': 32}
    }
    model = create_model(name, dummy_cfg)
    total_params = model.get_model_size()
    batches = math.ceil(total_params / SLOT_COUNT)
    cipher_size_mb = batches * BYTES_PER_BATCH / (1024 * 1024)
    plain_size_mb = total_params * 4 / (1024 * 1024)
    kb_per_batch = cipher_size_mb * 1024 / batches if batches > 0 else 0
    results.append({
        'model': name,
        'dataset': dataset,
        'input': f'{channels}x{size}x{size}',
        'classes': classes,
        'params': total_params,
        'plain_mb': plain_size_mb,
        'batches': batches,
        'kb_per_batch': kb_per_batch,
        'cipher_mb': cipher_size_mb,
        'expansion': cipher_size_mb / plain_size_mb if plain_size_mb > 0 else 0,
    })
    print(f"{name:15s} | {dataset:15s} | params={total_params:>8,} | {batches:>3} batches | {kb_per_batch:>6.1f} KB/batch | plain={plain_size_mb:>5.2f}MB | cipher={cipher_size_mb:>6.2f}MB | x{cipher_size_mb/plain_size_mb:.1f}")

with open('model_details.md', 'w', encoding='utf-8') as f:
    f.write('# 模型参数与 CKKS 密文大小对照表\n\n')
    f.write('**CKKS 配置**: `N=8192`, `slot_count=4096`, `coeff_mod=[60,40,40,60]`\n\n')
    f.write('**说明**: 每个 batch = 4096 个参数 = 1 个 CKKS 密文向量。密文大小按 ResNet20 实测数据估算（1 batch ≈ 290 KB）。\n\n')
    
    f.write('## 汇总表\n\n')
    f.write('| 模型名称 | 适用数据集 | 输入尺寸 | 类别数 | 总参数 | 明文大小 (MB) | Batch 数 | 每 Batch 密文 (KB) | 总密文大小 (MB) | 膨胀率 |\n')
    f.write('|---------|-----------|---------|-------|--------|--------------|---------|-------------------|----------------|--------|\n')
    for r in results:
        f.write(f"| {r['model']} | {r['dataset']} | {r['input']} | {r['classes']} | {r['params']:,} | {r['plain_mb']:.2f} | {r['batches']} | {r['kb_per_batch']:.1f} | {r['cipher_mb']:.2f} | {r['expansion']:.1f}x |\n")
    
    f.write('\n## 详细说明\n\n')
    f.write('### Batch 计算公式\n')
    f.write('```\n')
    f.write('batch_num = ceil(total_params / slot_count)\n')
    f.write('batch_num = ceil(total_params / 4096)\n')
    f.write('```\n\n')
    
    f.write('### 密文大小计算公式\n')
    f.write('```\n')
    f.write('cipher_size_MB = batch_num × 290 KB / 1024\n')
    f.write('```\n')
    f.write('其中 **290 KB/batch** 是根据 ResNet20 (67 batches = 19.45 MB) 实测数据估算。\n')
    f.write('在 CKKS 中，每个 batch 对应 1 个密文向量，密文大小只与多项式次数 N 和模数链长度有关，与打包的参数数量无关。因此所有模型的「每 Batch 密文大小」基本相同（≈ 290 KB）。\n\n')
    
    # ═════════════════════════════════════════════════════════════════
    # 新增：不同稀疏率下客户端选择的 batch 数量
    # ═════════════════════════════════════════════════════════════════
    f.write('\n## 不同稀疏率对应的客户端选择 Batch 数量\n\n')
    f.write('**说明**: 在 TopK 稀疏化策略下，客户端根据 `sparsity_rate` 选择最重要的 batch 上传。\n')
    f.write('`selected_batches = max(1, ceil(total_batches × sparsity_rate))`，即至少保留 1 个 batch。\n\n')
    
    sparsity_rates = [round(x * 0.1, 1) for x in range(1, 11)]  # 0.1 ~ 1.0
    
    # 表头
    header = '| 模型 | 数据集 | 总 Batch 数 |'
    for sr in sparsity_rates:
        header += f' {sr:.0%} |'
    f.write(header + '\n')
    
    # 分隔线
    sep = '|:---|:---|---:|'
    for _ in sparsity_rates:
        sep += '---:|'
    f.write(sep + '\n')
    
    # 数据行
    for r in results:
        total_batches = r['batches']
        line = f"| {r['model']} | {r['dataset']} | {total_batches} |"
        for sr in sparsity_rates:
            selected = max(1, math.ceil(total_batches * sr))
            line += f' {selected} |'
        f.write(line + '\n')
    
    f.write('\n### 稀疏率与通信开销关系（以 ResNet20 为例）\n\n')
    f.write('| 稀疏率 | 选择 Batch 数 | 每客户端密文大小 | 相对全量比例 |\n')
    f.write('|-------|-------------|----------------|------------|\n')
    total_batches_resnet20 = next(r['batches'] for r in results if r['model'] == 'resnet20' and r['dataset'] == 'CIFAR-10')
    for sr in sparsity_rates:
        selected = max(1, math.ceil(total_batches_resnet20 * sr))
        cipher_mb = selected * KB_PER_BATCH / 1024
        full_mb = total_batches_resnet20 * KB_PER_BATCH / 1024
        f.write(f"| {sr:.0%} | {selected} | {cipher_mb:.2f} MB | {cipher_mb/full_mb:.1%} |\n")
    
    f.write('\n> 注：稀疏率越高（越接近 100%），上传的 batch 越多，通信开销越大。当稀疏率=100% 时等同于全量上传。\n')
    
    f.write('\n## 模型结构分类\n\n')
    f.write('#### 1. 轻量模型 (< 100K 参数, < 25 batches)\n')
    f.write('适合快速验证、CPU 环境、低带宽场景。\n\n')
    for r in results:
        if r['params'] < 100000:
            f.write(f"- **{r['model']}** ({r['dataset']}): {r['params']:,} 参数, {r['batches']} batches, {r['cipher_mb']:.2f} MB\n")
    
    f.write('\n#### 2. 中等模型 (100K - 500K 参数, 25-125 batches)\n')
    f.write('标准联邦学习场景的主力模型。\n\n')
    for r in results:
        if 100000 <= r['params'] < 500000:
            f.write(f"- **{r['model']}** ({r['dataset']}): {r['params']:,} 参数, {r['batches']} batches, {r['cipher_mb']:.2f} MB\n")
    
    f.write('\n#### 3. 大型模型 (> 500K 参数, > 125 batches)\n')
    f.write('通信开销大，需要配合稀疏化或压缩策略使用。\n\n')
    for r in results:
        if r['params'] >= 500000:
            f.write(f"- **{r['model']}** ({r['dataset']}): {r['params']:,} 参数, {r['batches']} batches, {r['cipher_mb']:.2f} MB\n")

print("\n[OK] model_details.md generated")
