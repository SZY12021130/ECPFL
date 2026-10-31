"""
测试 MASER 在不同数据集上的通信量
"""
import sys
sys.path.append('E:/GithubProjects/ckks_fed_robustness/MASER-main')

from pympler import asizeof
from xmkckks_wrapper import MPHEServer
import config_FL

print("=" * 70)
print("MASER 不同数据集通信量测试")
print("=" * 70)

# 参数配置
num_clients = 25
slot_size = config_FL.get_slot_size()
print(f"客户端数量: {num_clients}")
print(f"Slot大小: {slot_size}")

# 各数据集的模型参数数量
datasets = {
    'mnist': {
        'model': 'lenet',
        'params': 61790,  # LeNet for MNIST
        'clients': 25
    },
    'fashion_mnist': {
        'model': 'lenet',
        'params': 61790,  # LeNet for FMNIST
        'clients': 25
    },
    'cifar10': {
        'model': 'conv8',
        'params': 269722,  # Conv8 for CIFAR10
        'clients': 5  # MASER源码只有5clients数据
    },
    'svhn': {
        'model': 'conv8',
        'params': 269722,  # Conv8 for SVHN
        'clients': 25  # 假设25clients
    }
}

# 创建服务器和客户端
server = MPHEServer(server_id=100)
clients = [MPHEServer(server_id=i) for i in range(1, num_clients + 1)]

# 测试密文大小
test_data = [0.1] * slot_size
single_ct = server.encryptFromPk(test_data)
single_ct_size = asizeof.asizeof(single_ct)

# 测试聚合密文大小
cts = [client.encryptFromPk(test_data) for client in clients]
agg_ct = cts[0]
for ct in cts[1:]:
    agg_ct = server.addCTs(agg_ct, ct)
agg_ct_size = asizeof.asizeof(agg_ct)

# 测试部分解密大小
pd_ct = clients[0].partialDecrypt(agg_ct)
pd_ct_size = asizeof.asizeof(pd_ct)

print(f"\n密文大小:")
print(f"  单密钥密文: {single_ct_size/1024/1024:.2f} MB")
print(f"  聚合密文: {agg_ct_size/1024/1024:.2f} MB")
print(f"  部分解密: {pd_ct_size/1024/1024:.2f} MB")
print(f"  膨胀比例: {agg_ct_size/single_ct_size:.2f}x")

print("\n" + "=" * 70)
print("各数据集通信量计算")
print("=" * 70)

for dataset_name, info in datasets.items():
    model_params = info['params']
    num_clients_ds = info['clients']
    threshold = 90  # 保留90%参数
    
    # 计算重要参数数量和slice数量
    important_params = int(model_params * threshold / 100)
    num_slices = (important_params // slot_size) + 1
    
    # 计算通信量
    upload_enc = single_ct_size * num_clients_ds * num_slices
    download_agg = agg_ct_size * num_clients_ds * num_slices
    upload_pd = pd_ct_size * num_clients_ds * num_slices
    total_per_round = upload_enc + download_agg + upload_pd
    total_50_rounds = total_per_round * 50
    
    print(f"\n【{dataset_name.upper()}】")
    print(f"  模型: {info['model']}")
    print(f"  参数数量: {model_params}")
    print(f"  客户端数量: {num_clients_ds}")
    print(f"  重要参数: {important_params}")
    print(f"  Slice数量: {num_slices}")
    print(f"  每轮通信量:")
    print(f"    加密上传: {upload_enc/1024/1024:.2f} MB")
    print(f"    聚合广播: {download_agg/1024/1024:.2f} MB")
    print(f"    解密份额: {upload_pd/1024/1024:.2f} MB")
    print(f"    总计: {total_per_round/1024/1024:.2f} MB = {total_per_round/1024/1024/1024:.2f} GB")
    print(f"  50轮总通信量: {total_50_rounds/1024/1024:.2f} MB = {total_50_rounds/1024/1024/1024:.2f} GB")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)