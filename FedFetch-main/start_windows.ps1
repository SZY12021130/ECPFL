# FedFetch Windows 本地一键启动脚本
# 解决 driver.py 在 Windows 下无法正确传递 conda 环境、PYTHONPATH 和解析 $FEDSCALE_HOME 的问题

param(
    [Parameter(Mandatory=$true)]
    [string]$ConfigFile
)

# ========== 请根据你的环境修改以下两行 ==========
$PythonExe = "D:\ProgramData\anaconda3\envs\concrete-env\python.exe"
$ProjectRoot = "E:\GithubProjects\FedFetch-main"
# ================================================

# 1. 读取 YAML（借助 Python 转成 JSON）
$jsonFile = [System.IO.Path]::GetTempFileName()
& $PythonExe -c "import yaml, json, sys; d=yaml.safe_load(open(sys.argv[1])); json.dump(d, open(sys.argv[2],'w'))" $ConfigFile $jsonFile
$config = Get-Content $jsonFile | ConvertFrom-Json
Remove-Item $jsonFile

# 2. 构造通用参数
$jobConf = @{}
foreach ($item in $config.job_conf) {
    $item.PSObject.Properties | ForEach-Object { $jobConf[$_.Name] = $_.Value }
}

$commonArgs = ""
foreach ($kv in $jobConf.GetEnumerator()) {
    $commonArgs += " --$($kv.Key) $($kv.Value)"
}

# 替换 YAML 中可能残留的 $FEDSCALE_HOME
$commonArgs = $commonArgs -replace '\$FEDSCALE_HOME', $ProjectRoot

$totalGpu = 0
$executorConfigsParts = @()
foreach ($ipGpu in $config.worker_ips) {
    $parts = $ipGpu -split ':'
    $ip = $parts[0]
    $gpuListStr = $parts[1] -replace '^\[|\]$', ''
    $gpuList = $gpuListStr -split ',' | ForEach-Object { [int]$_.Trim() }
    $sum = ($gpuList | Measure-Object -Sum).Sum
    $totalGpu += $sum
    $executorConfigsParts += "$ip`:[$(($gpuList -join ','))]"
}
$executorConfigs = $executorConfigsParts -join "="

# 3. 设置环境变量
$env:PYTHONPATH = "$ProjectRoot;$ProjectRoot\fedscale\dataloaders\rcnn\lib;$env:PYTHONPATH"

$expPath = ($config.exp_path -replace '\$FEDSCALE_HOME', $ProjectRoot)

# 4. 启动 Aggregator
$aggrCmd = "$PythonExe `"$expPath\$($config.aggregator_entry)`" $commonArgs --this_rank=0 --num_executors=$totalGpu --executor_configs=`"$executorConfigs`""
Write-Host "Starting Aggregator ..." -ForegroundColor Green
Write-Host $aggrCmd -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot'; $aggrCmd"

# 给 aggregator 留出初始化时间
Start-Sleep -Seconds 5

# 5. 启动 Executors
$rankId = 1
foreach ($ipGpu in $config.worker_ips) {
    $parts = $ipGpu -split ':'
    $gpuListStr = $parts[1] -replace '^\[|\]$', ''
    $gpuList = $gpuListStr -split ',' | ForEach-Object { [int]$_.Trim() }
    for ($cudaId = 0; $cudaId -lt $gpuList.Count; $cudaId++) {
        for ($i = 0; $i -lt $gpuList[$cudaId]; $i++) {
            $execCmd = "$PythonExe `"$expPath\$($config.executor_entry)`" $commonArgs --this_rank=$rankId --num_executors=$totalGpu --cuda_device=cuda:$cudaId"
            Write-Host "Starting Executor rank=$rankId cuda=$cudaId ..." -ForegroundColor Green
            Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ProjectRoot'; $execCmd"
            $rankId++
            Start-Sleep -Seconds 2
        }
    }
}

Write-Host "`nAll processes started. Check the new PowerShell windows for logs." -ForegroundColor Yellow
Write-Host "To monitor aggregated logs, see: $ProjectRoot\$($jobConf['job_name'])_logging.log" -ForegroundColor Yellow
