
import os
import torch
import torch.multiprocessing as mp
import numpy as np

import utils.min_hash as lsh
from utils.util import logging
from client import client_process
from server import server_process
from utils.dataset import load_dataset,load_exist
from utils.util import init_prop
from client import params_tolist
from models.model import LeNet_mnist,CNN_fmnist,resnet20,CNN_cifar
from models.resnet50 import resnet50

def model_init(dataset,device):
    """
    Model initialization.

    Args:
        dataset (`str`):
            Name of dataset.
        device (`str`):
            Training on GPU or MPS or CPU.

    Returns:
        model (`OrderDict`):
            Model for dataset.
    """
    if dataset == 'MNIST': 
        model = LeNet_mnist().to(device)
    elif dataset == 'FashionMNIST':
        model = CNN_fmnist().to(device)
        #model = resnet20(in_channels=1,num_classes=10).to(device) 
    elif dataset == 'CIFAR10':
        model = resnet20(in_channels=3,num_classes=10).to(device)
    elif dataset == 'CIFAR100':
        model = resnet50(in_channels=3,num_classes=100).to(device)
    else:
        raise ValueError("Datset name is invalid, please input MNIST, FashionMNIST, CIFAR10 or CIFAR100")
    return model

'''
args:main.py 中 arg_parse() 生成的所有超参数（如客户端数、加密算法、稀疏率等）
kwargs_IPC:进程间通信（IPC）参数集合（锁、队列、管道、事件等，由 main.py 中 IPC_init 生成）
数据集的结构：
client_train_datasets = [
    CustomSubset(  # 客户端0的训练集
        dataset=datasets.MNIST(根目录./data, 训练集),
        indices=np.array([12, 56, 89, ..., 59999])  # 约7500个MNIST训练样本索引（60000/8）
    ),
    CustomSubset(  # 客户端1的训练集
        dataset=datasets.MNIST(根目录./data, 训练集),
        indices=np.array([3, 18, 45, ..., 59998])  # 另一批7500个样本索引
    ),
    ...,  # 客户端2-7的CustomSubset实例
]
'''
def run(args,kwargs_IPC,device):
    """
    Run fucntion to launch server and clients processes.

    Args:
        args (`arg_parse`):
            Hyper-parameters.
        kwargs_IPC (`dict`):
            Parameters for IPC communication.    
        device (`str`):
            Training on GPU or MPS or CPU.
    Returns:
        None.
    """
    #Step 1：数据集加载 / 生成（联邦数据拆分）------------------------------------
    train_file = os.path.join(args.data_dir, args.dataset + '_train')
    if not os.path.exists(train_file): # 如果训练文件不存在
        client_train_datasets, client_test_datasets, data_info,server_test_sets = load_dataset(args)
        print("Generate new files!")
    else:    # 如果训练文件已存在
        client_train_datasets, client_test_datasets, data_info,server_test_sets = load_exist(args)
        print("Load last files!")


    #Step 2：客户端权重初始化------------------------------------
    """
   init_prop核心逻辑：计算每个客户端的「训练 / 测试权重」（通常按客户端样本数量占比分配）。
   联邦学习意义：联邦平均（FedAvg）时，服务端会根据train_weights加权聚合各客户端的模型参数，保证样本多的客户端对全局模型贡献更大。
    """
    train_weights,test_weights = init_prop(client_train_datasets,client_test_datasets, args.n_clients)

    #Step 3：日志输出（数据分布）------------------------------------
    logging("training weights: {}".format(train_weights),args)
    logging("testing weights:{}".format(test_weights),args)
    for idx in range(args.n_clients):
        logging('client{}, train samples {},test samples {}'.format(
                  idx,len(client_train_datasets[idx]),len(client_test_datasets[idx])),args)
    logging("data split finished!",args)

    kwargs = {'batch_size': args.batch_size,
              'shuffle': True,'drop_last':True}
    if args.cuda and torch.cuda.is_available():
        kwargs.update({'num_workers': 0,
                       'pin_memory': True,
                      })

    #Step 5：全局模型初始化------------------------------------
    '''
    逻辑：
    调用 model_init 生成对应数据集的基准模型；
    调用 client.py 中 params_tolist 将模型参数扁平化（便于加密 / 聚合）；
    计算模型总参数数量 total_sum（用于加密批次划分）。
    '''
    model = model_init(args.dataset,device)
    params_list,params_num,layer_shape = params_tolist(model)
    total_sum = sum(params_num.values())

    #Step 6：Paillier 加密参数补充（仅 Paillier 算法）
    if args.enc and args.algorithm == 'paillier':
        enc_tools = kwargs_IPC['enc_tools']
        enc_tools.update({'total_params':total_sum})
        kwargs_IPC.update({'enc_tools':enc_tools})

    #Step 7：加密批次数量计算（批量同态加密）------------------------------------
    '''
    核心公式：batch_num = 向上取整(总参数数 / 加密批次大小)；
    示例：总参数 10000，加密批次大小 4096 → batch_num=3（4096+4096+1808）；
    '''
    # number of batchs for processing
    batch_num = int(np.ceil(total_sum / args.enc_batch_size))
    if args.enc and args.isBatch:
        logging("Batch num:{}".format(batch_num),args)

    #Step 8：客户端选择（MinHash）参数初始化------------------------------------
    if args.isSelection:
        random_R = lsh.gen_random_R(input_len = total_sum, sim_len=args.sim_len)
        kwargs_IPC.update({'random_R':random_R,})

    #Step 9：启动服务端 + 客户端多进程
    '''
    核心逻辑：
    服务端：启动 1 个进程（rank=0），执行 server.py 中 server_process；
    客户端：启动 args.n_clients 个进程（rank=1~n_clients），每个进程执行 client.py 中 client_process；
    进程间通过 kwargs_IPC 中的管道 / 队列 / 事件通信，实现参数传输、聚合、客户端选择等逻辑。
    '''
    processes = []
    for rank in range(args.n_clients+1):
        # for server
        if rank == 0:#服务器进程
            p = mp.Process(target=server_process,args=(args,kwargs_IPC,total_sum,batch_num,train_weights,test_weights,server_test_sets,kwargs))
        # for clients
        else:#客户端进程
            p = mp.Process(target=client_process, args=(rank-1, args, model, device,
                                           client_train_datasets[rank-1], client_test_datasets[rank-1], kwargs,kwargs_IPC,train_weights))
        p.start()
        processes.append(p)
    for p in processes:
        p.join()
    
    #Step 10：结束日志
    logging('Final End',args)
