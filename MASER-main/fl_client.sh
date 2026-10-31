#!/bin/bash
# 声明这是bash脚本，告诉系统用bash解释器执行

# 以下两行是被你注释的关键代码（原本是启动核心服务的）
#echo "Starting key manager"  # 打印日志：开始启动密钥管理器
#python3 key_manager.py &     # 后台启动密钥管理器（&表示后台运行，不阻塞后续代码）
#sleep 10                     # 等待10秒，让密钥管理器完全启动，避免客户端连不上
#echo "Starting server"       # 打印日志：开始启动FL服务端
#python3 server.py &          # 后台启动FL服务端
#sleep 50                     # 等待50秒，让服务端初始化完成

# 1. 从config_FL.py中读取「客户端数量」（比如返回4，就会启动4个客户端）
range=$(python3 -c "from config_FL import num_client; print(num_client())")
new_range=$((range-1))  # 把数量转成「0到n-1」的范围（比如4个客户端就是0、1、2、3）

# 2. 循环启动每个客户端
for i in $(seq 0 $new_range); do  # seq 0 3 会生成0 1 2 3
    echo "Starting client $i"     # 打印日志：启动第i个客户端
    python3 client.py --partition=${i} &  # 后台启动第i个客户端（--partition指定客户端分区）
done

read  # 暂停脚本，等待用户按回车（防止脚本退出后，后台进程被终止）