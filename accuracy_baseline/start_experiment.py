import subprocess, os, time, sys

os.chdir(r"E:\GithubProjects\ckks_fed_robustness")
log_path = "accuracy_baseline/run_all_fix_serial.log"

with open(log_path, "w") as log:
    proc = subprocess.Popen(
        [r"D:\ProgramData\anaconda3\envs\concrete-env\python.exe", "accuracy_baseline/run_all_fix_serial.py"],
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
    )

# Write PID to file for monitoring
with open("accuracy_baseline/run_all_fix_serial.pid", "w") as f:
    f.write(str(proc.pid))

print(f"Started experiment PID={proc.pid} at {time.strftime('%H:%M:%S')}")
print(f"Log: {log_path}")
