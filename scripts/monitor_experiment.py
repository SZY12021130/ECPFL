import time
import subprocess
import sys

log_file = "scripts/strategy_comparison_run.log"
expected_strategies = ["random", "sticky", "sketch_clustering", "poc", "tifl", "haccs", "oort"]

print("[Monitor] Starting experiment monitor...")
while True:
    try:
        with open(log_file, "rb") as f:
            content = f.read().decode("utf-8", errors="ignore")
        
        # Count completed strategies
        found = []
        for s in expected_strategies:
            if f"Strategy created: {s}" in content:
                found.append(s)
        
        # Check if last strategy finished (has Final EMA after its creation)
        last_strategy_done = False
        if len(found) > 0:
            last_s = found[-1]
            idx = content.find(f"Strategy created: {last_s}")
            after = content[idx:]
            if "Final EMA" in after:
                last_strategy_done = True
        
        # Count rounds for current strategy
        round_count = content.count(" done  |  acc=")
        
        print(f"[Monitor] Strategies started: {len(found)}/7 ({found[-1] if found else 'none'})")
        print(f"[Monitor] Total round completions: {round_count}")
        
        if len(found) == 7 and last_strategy_done:
            print("[Monitor] All strategies completed!")
            break
        
        # Check if python process still running
        result = subprocess.run(["tasklist"], capture_output=True, text=True)
        if "python.exe" not in result.stdout:
            print("[Monitor] No python process found, exiting")
            break
            
    except Exception as e:
        print(f"[Monitor] Error: {e}")
    
    time.sleep(60)

print("[Monitor] Done")
