# Debug Session: ECPFL Communication Time Calculation

**Session ID**: ecpfl-comm-time  
**Status**: [RESOLVED]  
**Goal**: Ensure all `result_fix_pro` experiment reports contain the "Total Simulated Comm Time" field, and that TT equals pure network transmission time: Σ max(client_upload) + Σ max(client_download) per round.

## Hypotheses & Findings

1. **H1**: Most existing reports lack the "Total Simulated Comm Time" field because the reporting code only writes "Total Simulated Time" (which includes computation).
   - **Confirmed** for ECPFL older reports; other baselines already had CT Upload/Download Time fields.
2. **H2**: The current `communication.json` TT_S values for ECPFL are inconsistent—some are raw Total Simulated Time, others are incorrectly recomputed.
   - **Confirmed** and fixed. ECPFL TT_S now uses pure comm time.
3. **H3**: `upload_cost`/`download_cost` in `metrics.json` are aggregate per-round bytes, so per-client cost must be derived by dividing by the number of selected clients.
   - **Confirmed** and used for older ECPFL reports that lack `upload_time`/`download_time`.
4. **H4**: Report-generation code can be updated (or a post-processing script can be used) to inject the correct pure-comm time into every report and into `communication.json`.
   - **Confirmed**. Created `_ensure_all_comm_time.py` and `_verify_all_comm_time.py`.
5. **H5**: Running the corrected calculation across all experiments will produce TT values significantly lower than the old Total Simulated Time values (because computation time is excluded).
   - **Confirmed** for ECPFL. E.g., ECPFL-UN MNIST changed from 1759.44 s to 426.28 s.

## Actions Taken

1. Created `_ensure_all_comm_time.py` to:
   - Scan all `result_fix_pro` experiments across all baselines.
   - Compute `TT = CT Upload Time + CT Download Time` when available.
   - Fall back to `upload_cost/download_cost + client bandwidth` for older ECPFL reports missing `upload_time/download_time`.
   - Insert/update the `Total Simulated Comm Time` line in every `report.md`.
   - Update `communication.json` TT_S values.

2. Created `_verify_all_comm_time.py` to confirm every report's value matches `communication.json`.

## Verification Results

All 26 tracked experiments (4 datasets × 5 methods + extra ECPFL configs) pass verification:

```
[PASS] 所有报告和 communication.json 一致
```

Key ECPFL TT_S values after fix:
- ECPFL-UN MNIST: 426.28 s
- ECPFL-UN FMNIST: 288.21 s
- ECPFL-UN CIFAR-10: 1616.06 s
- ECPFL-UN SVHN: 801.28 s
- ECPFL-TH-0.1 MNIST: 410.37 s
- ECPFL-TH-0.3 FMNIST: 216.63 s
- ECPFL-TH-0.7 CIFAR-10: 612.60 s
- ECPFL-RK-0.1 MNIST: 80.31 s
- ECPFL-RK-0.3 FMNIST: 72.53 s
- ECPFL-RK-0.7 CIFAR-10: 1508.75 s

## Remaining Artifacts

- `_ensure_all_comm_time.py` — reusable update script
- `_verify_all_comm_time.py` — reusable verification script
- `debug-ecpfl-comm-time.md` — this session log
