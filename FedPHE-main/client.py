

import os
import torch
import torch.optim as optim
import torch.nn.functional as F
import numpy as np
from collections import OrderedDict
import time
from utils.util import logging
import random
import tenseal as ts
from threading import Thread
from encryption.ckks import ckks_enc,ckks_dec
from encryption.bfv import bfv_enc,bfv_dec
from encryption.paillier import paillier_enc,paillier_dec

import utils.min_hash as min_lsh

import pickle
from multiprocessing import shared_memory

'''
1. 模型参数序列化 / 反序列化
1.1 params_tolist(model)
作用：将模型参数转换为一维列表（扁平化），便于加密、传输和聚合（解决张量维度不兼容问题）。
关键逻辑：
遍历模型每层参数，记录每层形状（layer_shape）和参数数量（params_num）；
将每层参数展平为列表，最终拼接为全局一维列表；
关键公式 / 映射：
每层参数数量：params_num[key] = int(np.prod(local_state[key].shape))（key 为层名，prod 计算形状乘积）；
扁平化拼接：params_list = [b for a in params_list for b in a]（嵌套列表展平）。
'''
def params_tolist(model):
    """
    Model parameters converted to list

    Args:
        model:
            Model to be converted.
    Returns:
        params_list
            The converted parameter list.
        params_num
            The amount of parameters for each layer.
        layer_shape
            Shape of each layer.
    """ 
    model.to('cpu')
    local_state = model.state_dict()
    params_list = []
    layer_shape = {}
    params_num = {}
    layer_params = []
    for key in model.state_dict().keys():
        layer_shape[key] = local_state[key].shape
        params_num[key] = int(np.prod(local_state[key].shape))
        layer_params = local_state[key].reshape(params_num[key]).tolist()
        params_list.append(layer_params)
    params_list = [b for a in params_list for b in a]
    return params_list,params_num,layer_shape

'''
1.2 params_tomodel(model, global_list, params_num, layer_shape, args, params_list)
作用：将服务端聚合后的全局参数列表还原为模型参数（反序列化），稀疏场景下补全本地参数。
关键逻辑：
全量场景：直接按层拆分全局列表，重塑为张量后加载到模型；
稀疏场景（TopK/RandK）：全局列表中值为 0 的位置，用本地参数（params_list）补全；
关键公式 / 映射：
层参数切片：tmp = global_list[idx_cnt : idx_cnt + layer_size]（layer_size = params_num[key]）；
稀疏补全：if tmp[idx_tmp] == 0: tmp[idx_tmp] = params_list[idx_cnt + idx_tmp]；
张量重塑：torch.from_numpy(np.array(tmp).reshape(layer_shape[key]))。

'''
def params_tomodel(model,global_list,params_num,layer_shape,args,params_list):
    """
    Parameter list to model

    Args:
        model:
            The model obtained after parameter conversion.
        global_list
            Global model parameter list.
        params_num
            The amount of parameters for each layer.
        layer_shape
            Shape of each layer.
        args
            Hyper-parameters.
        params_list
            Local parameter list
    Returns:
        None
    """ 
    update_state = OrderedDict()
    model.to('cpu')
    idx_cnt = 0      
    if args.isSpars == 'topk' or args.isSpars == 'randk':
        for idx, key in enumerate(model.state_dict().keys()):
            layer_size = int(params_num[key])
            tmp = global_list[idx_cnt : idx_cnt + layer_size]

            # The part with a value of 0 is replaced by local parameters.
            for idx_tmp in range(len(tmp)):
                if tmp[idx_tmp] == 0 and ( idx_tmp == len(tmp)- 1 or tmp[idx_tmp+1]==0 ):
                    tmp[idx_tmp] = params_list[idx_cnt + idx_tmp]
                    # global_list[idx_cnt+idx_tmp] = tmp[idx_tmp]
            update_state[
                key] =  torch.from_numpy(np.array(tmp).reshape(layer_shape[key]))
            idx_cnt += layer_size            
    else:
        for idx, key in enumerate(model.state_dict().keys()):
            layer_size = int(params_num[key])
            tmp = global_list[idx_cnt:idx_cnt + layer_size]
            update_state[
                key] =  torch.from_numpy(np.array(tmp).reshape(layer_shape[key]))
            idx_cnt += layer_size

    model.load_state_dict(update_state)

'''
2. 客户端选择：MinHash 相似度计算
2.1 minHash(rank, random_R, global_list, params_list, args, quan_thres=0.05)
作用：生成客户端本地参数与全局参数的 MinHash 签名，用于服务端聚类选择代表性客户端（减少通信节点）。
关键公式 / 逻辑：
参数拼接：mat = np.concatenate((global_list.reshape(-1,1), params_list.reshape(-1,1)), axis=1)（全局 + 本地参数组成 2 列矩阵）；
量化（二值化）：quan_matrix = min_lsh.quan_params(mat, quan_thres)（绝对值 < 阈值设为 0，否则设为 1）；
生成签名矩阵：sim_mat = min_lsh.sigMatrixGen(quan_matrix, random_R, sim_len)（基于随机序列生成 MinHash 签名）；
提取客户端签名：minHash = (sim_mat[:,1]).tolist()（取本地参数对应的签名列）；
核心依赖公式（MinHash 签名生成）：
签名向量生成：对随机序列 random_R 遍历，记录每列第一个非零行号作为签名值（sigGen 方法）。
'''
def minHash(rank,random_R,global_list,params_list, args, quan_thres = 0.05):
    '''
    quan_thres: Tthreshold value used for quantization
    sim_len: Number of hash functions
    '''
    sim_len = args.sim_len

    mat = np.concatenate((np.array(global_list).reshape(-1,1),np.array(params_list).reshape(-1,1)),axis=1)

    quan_matrix = min_lsh.quan_params(mat,quan_thres)

    sim_mat = min_lsh.sigMatrixGen(quan_matrix,random_R, sim_len)

    # client_sim2 = min_lsh.dim_reduce_sim(sim_mat)

    minHash = (sim_mat[:,1]).tolist()
    return minHash

'''
3. 辅助：掉队节点模拟
3.1 straggler(rank)
作用：模拟联邦学习中的 “掉队节点”（Straggler），故意让指定客户端休眠，测试系统鲁棒性。
关键逻辑：
随机休眠时间：timewait = np.random.randint(10,15)；
客户端 1/2 触发休眠：if rank in [1,2]: time.sleep(timewait)。
'''
def straggler(rank):
    timewait = np.random.randint(10,15)
    if rank == 1:
        time.sleep(timewait)
    if rank == 2:
        time.sleep(timewait)

'''
4. 核心：客户端主进程
4.1 client_process(rank, args, model, device, dataset, test_dataset, kwargs, kwargs_IPC, train_weights)
作用：客户端主逻辑，串联 “本地训练 → 参数加密 / 发送 → 接收全局参数 → 解密 / 更新模型 → 测试 / MinHash 生成 → 客户端选择” 全流程。
核心步骤 & 关键公式：
【初始化】：加载通信管道 / 队列、优化器、数据加载器，初始化权重 self_weight = train_weights[rank]；
【本地训练】：调用 train_epoch 训练模型，生成本地参数列表 params_list；
【参数加密 & 发送】：
加密权重缩放：params_list = (np.array(params_list) * self_weight).tolist()（Paillier/BFV 场景，明文权重加权）；
稀疏（TopK）：cipher, mask = enc_params(...) → 发送 [rank, mask, cipher]；
全量 / RandK：cipher = enc_params(...) → 发送 [rank, cipher]；
接收全局参数 & 解密：
等待服务端聚合：e.wait() → 从队列取 [involved_frac, global_weights]；
解密：global_weights = dec_params(...) / involved_frac（involved_frac 为聚合权重和，归一化）；
模型更新：调用 params_tomodel 加载全局参数，稀疏场景补全本地参数；
模型测试：client_acc, client_loss = test_epoch(...) → 发送精度 / 损失到服务端；
客户端选择：
生成 MinHash 签名：client_hash = minHash(...) → 发送到服务端；
读取服务端选中列表：若未被选中，self_flag = False（停止发送参数）；若选中，更新权重 self_weight = clients_weights[idx]；
'''

def client_process(rank, args, model, device,dataset, test_dataset, kwargs,kwargs_IPC,train_weights):
    # 1. 随机种子固定（保证可复现）
    torch.manual_seed(args.seed + rank)
    # 2. 从IPC通信字典中获取客户端专属的通信组件（队列/管道/锁/事件等）
    queue = kwargs_IPC['queues'][rank]# 接收服务端全局参数的队列
    e = kwargs_IPC['e']# 等待服务端聚合完成的事件
    lock = kwargs_IPC['lock']# 日志打印锁
    pipe = kwargs_IPC['client_pipes'][rank][0]# 向服务端发送本地参数的管道
    flag = kwargs_IPC['flag'] # 训练终止标志（服务端控制）
    e_server = kwargs_IPC['e_server'] # 等待服务端客户端选择完成的事件
    acc_queue = kwargs_IPC['acc_queue']
    self_weight = train_weights[rank]# 该客户端的聚合权重（样本数占比）
    acc_pipe = kwargs_IPC['send_pipes'][rank][0]

    # 3. 加密工具初始化（仅Paillier算法需要）
    if args.enc and args.algorithm == 'paillier':
        enc_tools = kwargs_IPC['enc_tools']
    else:
        enc_tools = {}

    if args.isSelection:
        random_R = kwargs_IPC['random_R']

    hash_queue = kwargs_IPC['hash_queue']
    train_loader = torch.utils.data.DataLoader(dataset, **kwargs)
    test_loader = torch.utils.data.DataLoader(test_dataset, **kwargs)
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    
    if rank == 0:
        spars_list = []
    sum_masks = []
    epoch = 0# 客户端本地迭代轮次

    self_flag = True# 标记当前客户端是否被选中参与本轮训练
    acc_list = []
    
    while not flag.value:# flag由服务端控制，为True时终止训练
        
        #epoch_begin = time.time()

        #train_begin = time.time()
        for _ in range(args.local_epochs):
            train_epoch(epoch, args, model, device, train_loader, optimizer, rank)
        #train_end = time.time()
        #logging("id:{},train time:{}".format(rank,train_end-train_begin),args)

        params_list,params_num,layer_shape = params_tolist(model)
        total_sum = sum(params_num.values())
        if args.enc and args.algorithm == 'paillier':
            enc_tools.update({'total_params':total_sum})

        # if selected 
        if self_flag:     # self_flag=True：当前客户端被选中参与本轮
            # if epoch > 0 :   
            #     straggler(rank)
            if args.enc:
                # 1. 权重加权（Paillier/BFV算法：本地先乘权重，减少服务端计算）
                if args.algorithm == 'paillier':
                    params_list = (np.array(params_list) * self_weight).tolist()
                if args.algorithm == 'bfv':
                    params_list = (np.array(params_list) * self_weight).tolist()
                # 2. 不同稀疏策略的加密逻辑
                if args.isSpars == 'topk' :
                    # TopK稀疏：只加密最重要的TopK%参数，返回密文+掩码（标记哪些batch被选中
                    #enc_begin = time.time()
                    cipher, mask = enc_params(params_list,enc_tools, args)
                    pipe.send([rank,mask,cipher])
                    #enc_end = time.time()
                    #logging("id:{},enc time:{}".format(rank,enc_end-enc_begin),args)
                    # lock.acquire()
                    # logging("client {}, send mask {}.".format(rank,mask),args)
                    # lock.release()
                elif args.isSpars == 'randk':
                    # RandomK稀疏：随机选K%参数加密，返回密文+随机列表
                    cipher, randk_list = enc_params(params_list,enc_tools,args,epoch = epoch)
                    if rank == 0:
                        logging("epoch:{},rand_K:{}".format(epoch,randk_list),args)
                    pipe.send([rank,cipher])   # 发送：客户端ID+密文

                elif args.isSpars == 'full':
                    #enc_begin = time.time()
                    # 无稀疏：加密所有参数
                    cipher = enc_params(params_list,enc_tools,args,epoch = epoch)
                    pipe.send([rank,cipher])# 发送：客户端ID+密文
                    #enc_end = time.time()
                    #logging("id:{},enc time:{}".format(rank,enc_end-enc_begin),args)
            else:# 不加密：直接发送原始参数列表
                pipe.send([rank,params_list])
            # lock.acquire()
            # logging("client {}, send params {}.".format(rank,params_list[0]),args)
            # lock.release()

        if flag.value:
            break       

        # Waiting for server aggregation

        # 2. 阻塞等待服务器完成聚合（服务器聚合后会调用e.set()）
        e.wait()# 阻塞等待：服务端完成所有客户端参数聚合后，触发该事件

        global_list = queue.get()# 从队列获取服务端返回的全局参数
        involved_frac = global_list[0] # 参与聚合的客户端权重和（或掩码和）
        global_weights = global_list[1] # 聚合后的全局参数（密文/明文）

        if args.enc:# 开启加密：解密全局参数
            if args.isSpars == 'topk':
                #dec_begin = time.time()
                sum_masks = involved_frac
                global_weights = (dec_params(global_weights,sum_masks,enc_tools, args)).tolist()
                #dec_end = time.time()
                #logging("id:{},dec time:{}".format(rank,dec_end-dec_begin),args)
            elif args.isSpars == 'randk':
                global_weights = (dec_params(global_weights,sum_masks,enc_tools, args, randk_list)).tolist()
            else:
                # 无稀疏：解密后除以参与权重和，完成归一化
                #dec_begin = time.time()
                global_weights = (dec_params(global_weights,sum_masks, enc_tools,args) / involved_frac).tolist()
                #dec_end = time.time()
                #logging("id:{},dec time:{}".format(rank,dec_end-dec_begin),args)
            global_weights = global_weights[:total_sum]# 截断到模型参数长度
        else:#不加密：直接归一化
            global_weights = (np.array(global_weights) / involved_frac).tolist()
   
        # lock.acquire()
        # print('client{},receive{}'.format(rank,global_weights[0])) 
        # lock.release()
        params_list,params_num,layer_shape = params_tolist(model)

        #步骤 6：更新本地模型（全局参数覆盖）
        #稀疏场景下（TopK / RandomK）：未被选中的参数位置用本地参数填充（保证模型参数完整性）。
        params_tomodel(model,global_weights,params_num,layer_shape,args,params_list)

        if args.enc:#步骤 7：本地测试与精度上报
            client_acc,client_loss = test_epoch(model, device, test_loader)
            acc_pipe.send([rank,client_acc,client_loss])
            print('client{},acc:{},loss:{}'.format(rank,client_acc,client_loss))
        #步骤8：客户端选择（可选，args.isSelection = True）
        if args.isSelection:
            # 1. 计算MinHash：本地模型与全局模型的相似度哈希
            client_hash = minHash(rank, random_R,global_weights,params_list,args)
            hash_queue.put([rank,client_hash])# 发送哈希值给服务端

            if flag.value:
                break

            # Wait for server to make client selection

            e_server.wait()
            # 2. 读取服务端选择结果
            selected_file = os.path.join(args.data_dir, args.dataset + 'selected')
            with open(selected_file, "rb") as f:
                clients_bytes = f.read()
                clients_share = list(pickle.loads(clients_bytes))[0]
                clients_weights = list(pickle.loads(clients_bytes))[1]

            if rank not in clients_share:
                self_flag = False# 未被选中，下一轮不发送参数
            else:#
                self_flag = True # 被选中，更新权重+
                idx = clients_share.index(rank)
                self_weight = clients_weights[idx]      
        #epoch_end = time.time()
 
        epoch += 1

    lock.acquire()#acquire()：获取锁。如果锁已被其他进程 / 线程占用，则阻塞（等待）直到锁被释放；如果未被占用，立即获取锁。
    logging("client {} finished!".format(rank),args)# 打印终止日志
    lock.release()#release()：释放锁。必须在acquire()之后调用，否则会抛出异常。
    return

'''
5. 模型测试
5.1 test(args, model, device, dataset, kwargs)
作用：封装测试逻辑，调用 test_epoch 计算模型在测试集上的精度 / 损失。
关键逻辑：初始化数据加载器 → 调用 test_epoch 返回结果。
'''
def test(args, model, device, dataset, kwargs):
    torch.manual_seed(args.seed)

    test_loader = torch.utils.data.DataLoader(dataset, **kwargs)

    return test_epoch(model, device, test_loader)

'''
6. 模型训练
6.1 train_epoch(epoch, args, model, device, data_loader, optimizer, rank)
作用：客户端本地训练一轮模型，基于交叉熵损失反向传播更新参数。
关键公式 / 逻辑：
损失计算：loss = torch.nn.CrossEntropyLoss()(output, target)；
反向传播：optimizer.zero_grad() → loss.backward() → optimizer.step()；
（可选）日志输出：记录训练轮次、损失、进度。
'''
def train_epoch(epoch, args, model, device, data_loader, optimizer,rank):
    model.to(device)
    model.train()
    loss_fn = torch.nn.CrossEntropyLoss()
    for batch_idx, (data, target) in enumerate(data_loader):
        
        output = model(data.to(device))
        target = target.to(device)
        # loss = F.nll_loss(output, target.to(device))
        # loss = torch.nn.CrossEntropyLoss()(output, target.to(device))
        loss = loss_fn(output, target)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        # if batch_idx == len(data_loader) - 1:      
        #     logging('client {}\tTrain Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
        #         rank, epoch, batch_idx * len(data), len(data_loader.dataset),
        #         100. * batch_idx / len(data_loader), loss.item()))
     
'''
5.3 test_epoch(model, device, data_loader)
作用：核心测试方法，计算模型在测试集上的平均损失和分类精度。
关键公式 / 逻辑：
损失计算：
交叉熵损失累加：test_loss += F.cross_entropy(output, target.to(device), reduction='sum')；
平均损失：test_loss /= len(data_loader.dataset)；
精度计算：
正确预测数：correct += pred.eq(target.to(device)).sum().item()（pred = output.max(1)[1] 取预测类别）；
分类精度：client_acc = correct / len(data_loader.dataset)；
结果格式化：
test_loss = round(float(test_loss), 3)；
client_acc = round(client_acc, 4) * 100（转为百分比）
'''
def test_epoch(model, device, data_loader):
    model.to(device)
    model.eval()
    correct = 0
    test_loss = 0
    with torch.no_grad():
        for data, target in data_loader:
            output = model(data.to(device))
            #test_loss += F.nll_loss(output, target.to(device), reduction='sum').item() # sum up batch loss
            #test_loss += torch.nn.CrossEntropyLoss()(output, target.to(device),reduction='sum')
            test_loss +=F.cross_entropy(output, target.to(device), reduction='sum')
            pred = output.max(1)[1] # get the index of the max log-probability
            correct += pred.eq(target.to(device)).sum().item()
    test_loss /= len(data_loader.dataset)
    #print("loss",test_loss)
    # print('\nTest set: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)\n'.format(
    #     test_loss, correct, len(data_loader.dataset),
    #     100. * correct / len(data_loader.dataset)))
    client_acc = correct / len(data_loader.dataset)

    # set the return variable format
    test_loss = round(float(test_loss),3) 
    client_acc = round(client_acc,4)*100 
    return client_acc, test_loss

'''
7. 加密 / 解密核心方法
7.1 enc_params(params_list, enc_tools, args, epoch=0)
作用：根据指定加密算法（CKKS/BFV/Paillier）加密本地参数列表，支持稀疏（TopK/RandK）和全量加密。
'''
# Encrypt all parameters of a client
def enc_params(params_list,enc_tools,args,epoch = 0):
    if args.algorithm == 'ckks':
        ckks_file = os.path.join(args.data_dir + 'context_params')
        with open(ckks_file, "rb") as f:
            params = f.read()
        ckks_ctx = ts.context_from(params) 
        return ckks_enc(params_list,ckks_ctx,isBatch=args.isBatch,batch_size=args.enc_batch_size,
                        topk=args.topk,round = epoch,randk_seed=args.randk_seed, is_spars = args.isSpars)
    elif args.algorithm =='paillier':
        cls_paillier = enc_tools['cls_paillier']
        return  paillier_enc(params_list,cls_paillier,args)
    elif args.algorithm == 'bfv':
        bfv_file = os.path.join(args.data_dir + 'bfv_ctx')
        with open(bfv_file, "rb") as f:
            params = f.read()
        bfv_ctx = ts.context_from(params)      
        return bfv_enc(params_list,bfv_ctx,args)
    else:
        raise ValueError("please select valid algorithm")
'''
7.2 dec_params(cipher_list, sum_masks, enc_tools, args, randk_list=[])
作用：解密服务端聚合后的密文参数列表，还原为明文参数，支持稀疏场景的掩码补全。
'''
# Decrypt all parameters of a client
def dec_params(cipher_list,sum_masks, enc_tools,args, randk_list = []):
    if args.algorithm == 'ckks':
        ckks_file = os.path.join(args.data_dir + 'context_params')
        with open(ckks_file, "rb") as f:
            params = f.read()
        ckks_ctx = ts.context_from(params) 
        sk = ckks_ctx.secret_key()
        return ckks_dec(cipher_list,ckks_ctx,sk,args.isBatch,randk_list,sum_masks,args.enc_batch_size)
    elif args.algorithm =='paillier':
        cls_paillier = enc_tools['cls_paillier']
        total_params = enc_tools['total_params']
        return  paillier_dec(cipher_list,cls_paillier,total_params,args)
    elif args.algorithm == 'bfv':
        bfv_file = os.path.join(args.data_dir + 'bfv_ctx')
        with open(bfv_file, "rb") as f:
            params = f.read()
        bfv_ctx = ts.context_from(params) 
        sk = bfv_ctx.secret_key()
        return bfv_dec(cipher_list,bfv_ctx,sk,args.isBatch,args.quan_bits,args.n_clients,sum_masks,args.enc_batch_size)    
    else:
        raise ValueError("please select valid algorithm")  

