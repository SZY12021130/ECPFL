# FedFetch Windows 启动问题诊断与解决策略

> 本文档记录了你当前在 Windows 环境下启动 FedFetch 时遇到的全部障碍，以及对应的解决步骤。

---

## 一、问题诊断总结

### 1. Python 依赖问题（已修复）
- **`pkg_resources` 缺失** → `setuptools 82.0.1` 安装损坏，通过降级到 `69.5.1` 解决。
- **`wandb` 版本不兼容** → 已确认 `wandb 0.15.12`（<0.16）可正常工作。

### 2. `fedscale driver submit/start` 在 Windows 上启动失败（核心问题）
**FedScale 的 `docker/driver.py` 是为 Linux 设计的**，在 Windows PowerShell 上本地运行时会暴露三个兼容性问题：

#### 问题 A：子进程使用 `cmd.exe`，找不到 Conda 环境的 Python
`driver.py` 用 `subprocess.Popen(..., shell=True)` 启动 aggregator/executor。在 Windows 上，`shell=True` 默认调用 `cmd.exe`，而 `cmd.exe` 的 `PATH` 中 `python` 指向的是 **Anaconda base 环境**（`D:\ProgramData\anaconda3\python.exe`），不是你的 `concrete-env`。因此子进程一启动就因为缺少 `wandb`、`tensorflow` 等包而崩溃。

#### 问题 B：`$FEDSCALE_HOME` 环境变量在 YAML 中无法展开
配置文件中写了：
```yaml
exp_path: $FEDSCALE_HOME/examples/prefetch
```
Windows 不会自动展开这个变量，导致 `driver.py` 构造出的路径变成：
```
E:\GithubProjects\FedFetch-main\$FEDSCALE_HOME\examples\prefetch\aggregator.py
```
直接触发 `FileNotFoundError`。

#### 问题 C：`PYTHONPATH` 未传递给子进程
即使你在 PowerShell 里设置了 `$env:PYTHONPATH`，`cmd.exe` 子进程也继承不到。这导致 `import fedscale` 失败（`ModuleNotFoundError: No module named 'fedscale'`）。

#### 问题 D：RCNN 内部 `datasets` 模块路径缺失
FedScale `aggregator.py` 顶层导入了 `combined_roidb`，该模块在 Windows 上会因为 `import datasets`（RCNN 子模块）找不到路径而崩溃。需要把 `fedscale/dataloaders/rcnn/lib` 加入 `PYTHONPATH`。

### 3. 数据集未下载
当以上环境/启动问题解决后，executor 会开始加载数据。如果 FEMNIST / Speech / OpenImage 数据集尚未下载，会报：
```
FileNotFoundError: [Errno 2] No such file or directory: '.../train.csv'
```

---

## 二、解决策略

### 策略 1：放弃 `fedscale driver submit`，改用“手动分别启动”（推荐）

这是 Windows 上最可靠的方式。我已经为你写好了自动化脚本 **`start_windows.ps1`**，它会：
1. 解析 YAML 配置文件；
2. 自动把 `$FEDSCALE_HOME` 替换为绝对路径；
3. 设置正确的 `PYTHONPATH`（包含 RCNN lib 路径）；
4. 使用 `concrete-env` 的 Python 解释器；
5. 用 `Start-Process` 在新窗口中分别启动 **Aggregator** 和所有 **Executors**。

#### 使用步骤

**Step 1：下载数据集（如果还没下）**
```powershell
cd E:\GithubProjects\FedFetch-main
conda activate concrete-env
python -m fedscale.cloud.dataset.femnist --download  # 或按 README 中的方式
```
> 更简单的做法：运行 README 中的 `fedscale dataset download femnist`，或者直接把数据放到 `benchmark/dataset/data/femnist/` 目录下。

**Step 2：修改脚本中的路径（必须）**
打开 `start_windows.ps1`，确认前两行与你的机器一致：
```powershell
$PythonExe = "D:\ProgramData\anaconda3\envs\concrete-env\python.exe"
$ProjectRoot = "E:\GithubProjects\FedFetch-main"
```

**Step 3：运行脚本**
```powershell
cd E:\GithubProjects\FedFetch-main
.\start_windows.ps1 -ConfigFile "benchmark/configs/perf/femnist/STC_prefetch.yml"
```

你会看到多个新的 PowerShell 窗口弹出：
- 第一个窗口运行 **Aggregator**；
- 后续窗口运行 **6 个 Executor**（根据你的 YAML 配置 `localhost:[6]`）。

**Step 4：观察日志**
- Aggregator 日志：`benchmark/logs/STC_femnist_prefetch/<时间戳>/logs/aggregator/log`
- Executor 日志：`benchmark/logs/STC_femnist_prefetch/<时间戳>/logs/executor/log`
- 合并日志：项目根目录下的 `STC_femnist_prefetch_logging.log`

### 策略 2：如果你坚持用 `driver.py`（需改代码）

如果你不想用手动启动，可以修改 `docker/driver.py` 的以下位置：

1. **将 `python` 替换为 concrete-env 的绝对路径**：
   在 `driver.py` 中把：
   ```python
   ps_cmd = f" python {yaml_conf['exp_path']}/{yaml_conf['aggregator_entry']} ..."
   worker_cmd = f" python {yaml_conf['exp_path']}/{yaml_conf['executor_entry']} ..."
   ```
   改为：
   ```python
   python_exe = r"D:\ProgramData\anaconda3\envs\concrete-env\python.exe"
   ps_cmd = f" {python_exe} {yaml_conf['exp_path']}/{yaml_conf['aggregator_entry']} ..."
   worker_cmd = f" {python_exe} {yaml_conf['exp_path']}/{yaml_conf['executor_entry']} ..."
   ```

2. **在 `process_cmd` 开头加入环境变量注入**：
   ```python
   os.environ['PYTHONPATH'] = r"E:\GithubProjects\FedFetch-main;E:\GithubProjects\FedFetch-main\fedscale\dataloaders\rcnn\lib"
   ```

3. **将 YAML 中的 `$FEDSCALE_HOME` 全部替换为绝对路径**（如上面我已经帮你修改过的 `STC_prefetch.yml`）。

> ⚠️ 即便如此，由于 Windows 的 `subprocess.Popen(shell=True)` 行为与 Linux 差异较大，**仍然推荐使用策略 1 的 `start_windows.ps1` 脚本**。

### 策略 3：使用 WSL2 / Linux 虚拟机（最省心的终极方案）

FedScale 的开发与测试主要在 Linux 上进行，`driver.py` 的进程调度、SSH、shell 展开都依赖 Linux 特性。如果你后续要频繁做实验，**建议在 WSL2（Windows Subsystem for Linux）里安装 Ubuntu，然后在 WSL2 中运行 FedFetch**。这样所有命令（包括 `fedscale driver submit`）都能原样工作，无需任何 workaround。

---

## 三、已验证成功的启动链路

以下是我验证过的正确命令（供排查时参考）：

**启动 Aggregator：**
```powershell
$env:PYTHONPATH="E:/GithubProjects/FedFetch-main;E:/GithubProjects/FedFetch-main/fedscale/dataloaders/rcnn/lib"
D:\ProgramData\anaconda3\envs\concrete-env\python.exe examples/prefetch/aggregator.py `
  --job_name STC_femnist_prefetch --log_path E:/GithubProjects/FedFetch-main/benchmark `
  --num_participants 30 --data_set femnist ...（其余参数见配置文件）... `
  --this_rank=0 --num_executors=6 --executor_configs=localhost:[6]
```

**启动 Executor（在新窗口中）：**
```powershell
$env:PYTHONPATH="E:/GithubProjects/FedFetch-main;E:/GithubProjects/FedFetch-main/fedscale/dataloaders/rcnn/lib"
D:\ProgramData\anaconda3\envs\concrete-env\python.exe examples/prefetch/executor.py `
  --job_name STC_femnist_prefetch --log_path E:/GithubProjects/FedFetch-main/benchmark `
  --num_participants 30 --data_set femnist ...（其余参数同配置文件）... `
  --this_rank=1 --num_executors=6 --cuda_device=cuda:0
```

确认 Aggregator 成功监听的标志：
```powershell
netstat -ano | findstr 29500
# 应显示 TCP 0.0.0.0:29500 LISTENING
```

---

## 四、快速检查清单

在运行 `start_windows.ps1` 之前，请确认：
- [ ] `concrete-env` 已激活，且 `pip list` 中能看到 `wandb`、`torch`、`grpcio` 等核心包
- [ ] `setuptools` 版本 ≤ 69.5.1（否则 `pkg_resources` 会报错）
- [ ] `start_windows.ps1` 前两行的 `$PythonExe` 和 `$ProjectRoot` 已改为你的实际路径
- [ ] YAML 配置文件中 `data_dir` 指向的 FEMNIST 数据集已下载（`train.csv` 存在）
- [ ] 29500 端口没有被其他程序占用

---

## 五、结论

你的 FedFetch 项目本身没有任何代码错误。当前无法启动完全是因为 **FedScale 的 `driver.py` 没有兼容 Windows 的进程调度、环境变量传递和 Shell 语法**。使用我提供的 `start_windows.ps1` 脚本手动分别启动 Aggregator 和 Executor 是当前 Windows 环境下最稳妥的方案。
