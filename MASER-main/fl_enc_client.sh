#!/bin/bash
# 声明Python路径（避免系统默认Python，确保用conda环境的Python）
PYTHON_PATH="/d/ProgramData/anaconda3/envs/concrete-env/python.exe"

# 第一步：启动密钥管理器
echo "=== Starting Key Manager ==="
$PYTHON_PATH key_manager.py &
# 等待10秒，确保密钥管理器启动并监听端口
sleep 10

# 第二步：启动FL服务端
echo "=== Starting FL Server ==="
$PYTHON_PATH server.py &
# 等待30秒，让服务端完成初始化（根据你的机器性能调整）
sleep 30

# 第三步：启动所有客户端
echo "=== Starting Clients ==="
# 读取客户端数量
range=$($PYTHON_PATH -c "from config_FL import num_client; print(num_client())")
new_range=$((range-1))

# 循环启动每个客户端（逐个启动，避免端口冲突）
for i in $(seq 0 $new_range); do
    echo "Starting client $i..."
    $PYTHON_PATH client.py --partition=${i} &
    # 每个客户端间隔1秒启动
    sleep 1
done

# 暂停脚本，防止退出（按回车才会结束）
echo "=== All processes started. Press Enter to exit ==="
read