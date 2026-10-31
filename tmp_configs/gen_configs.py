import os

def safe_modify(src, dst, alpha, mutual=None):
    with open(src, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    result = []
    in_data_block = False
    in_root_ptopk = False
    root_client_residual_idx = -1
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if stripped.startswith('data:'):
            in_data_block = True
        elif in_data_block and stripped and not stripped.startswith('#') and ':' in stripped and not line.startswith('  '):
            in_data_block = False
        
        if in_data_block and stripped.startswith('alpha:'):
            indent = len(line) - len(line.lstrip())
            line = ' ' * indent + f'alpha: {alpha}\n'
        
        # Track root-level ptopk (0-space indent)
        if stripped == 'ptopk:' and not line.startswith(' '):
            in_root_ptopk = True
        elif in_root_ptopk and stripped and not line.startswith(' '):
            in_root_ptopk = False
        
        if in_root_ptopk and stripped == 'client_residual:':
            root_client_residual_idx = len(result)
        
        result.append(line)
    
    # Insert mutually_exclusive after root client_residual
    if mutual is not None and root_client_residual_idx >= 0:
        insert_line = '    mutually_exclusive: ' + ('true\n' if mutual else 'false\n')
        result.insert(root_client_residual_idx + 1, insert_line)
    
    with open(dst, 'w', encoding='utf-8') as f:
        f.writelines(result)
    print(f"Created: {os.path.basename(dst)} (alpha={alpha}, mutual={mutual})")

base = 'accuracy_niid'
safe_modify(f'{base}/cifar10-resnet20/experiment_20260531_193511/config.yaml', 'tmp_configs/cifar10_a5_mutual.yaml', 5, True)
safe_modify(f'{base}/cifar10-resnet20/experiment_20260531_193511/config.yaml', 'tmp_configs/cifar10_a5_nonmutual.yaml', 5, False)
safe_modify(f'{base}/cifar10-resnet20/experiment_20260531_193511/config.yaml', 'tmp_configs/cifar10_a10_mutual.yaml', 10, True)
safe_modify(f'{base}/cifar10-resnet20/experiment_20260531_193511/config.yaml', 'tmp_configs/cifar10_a10_nonmutual.yaml', 10, False)

safe_modify(f'{base}/mnist-lenet/experiment_20260531_133859/config.yaml', 'tmp_configs/mnist_a5.yaml', 5, False)
safe_modify(f'{base}/mnist-lenet/experiment_20260531_133859/config.yaml', 'tmp_configs/mnist_a10.yaml', 10, False)

safe_modify(f'{base}/fashion_mnist-cnn_fmnist/experiment_20260531_160147/config.yaml', 'tmp_configs/fmnist_a5.yaml', 5, False)
safe_modify(f'{base}/fashion_mnist-cnn_fmnist/experiment_20260531_160147/config.yaml', 'tmp_configs/fmnist_a10.yaml', 10, False)

print("\nAll 8 configs created!")
