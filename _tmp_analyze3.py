import os, json, yaml

exps = ['experiment_20260510_155458', 'experiment_20260510_161117']

for exp in exps:
    d = os.path.join('results', exp)
    cfg_path = os.path.join(d, 'config.yaml')
    met_path = os.path.join(d, 'metrics.json')
    log_path = os.path.join(d, 'experiment.log')
    
    print(f"\n{'='*100}")
    print(f"Exp: {exp}")
    
    if os.path.exists(cfg_path):
        with open(cfg_path, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)
        sys = cfg.get('system', {})
        pf = cfg.get('prefetch', {})
        print(f"  num_clients={sys.get('num_clients')}, num_rounds={sys.get('num_rounds')}, num_epochs={sys.get('num_epochs')}")
        print(f"  client_sampling={sys.get('client_sampling_rate')}")
        print(f"  prefetch_enabled={pf.get('enable_prefetch')}, warmup={pf.get('warmup_round')}, max_prefetch={pf.get('max_prefetch_round')}")
        print(f"  use_sticky={pf.get('use_sticky_sampling')}, overcommitment={pf.get('overcommitment')}")
    
    if os.path.exists(met_path):
        with open(met_path, 'r', encoding='utf-8') as f:
            m = json.load(f)
        
        accs = m.get('test_acc', [])
        losses = m.get('test_loss', [])
        real_times = m.get('total_round_time', [])
        sim_times = m.get('total_round_time_simulated', [])
        real_cpu_times = m.get('total_round_real_time', [])
        comms = m.get('total_communication_cost', [])
        upload_costs = m.get('upload_cost', [])
        download_costs = m.get('download_cost', [])
        fetch_times = m.get('fetch_time', [])
        pf_download = m.get('prefetch_download_cost', [])
        pf_broadcast = m.get('prefetch_broadcast_cost', [])
        
        print(f"\n  Round-by-round:")
        print(f"  {'R':<3} {'acc':<7} {'loss':<8} {'real_t':<10} {'sim_t':<10} {'real_cpu':<10} {'comm(MB)':<10} {'upload':<10} {'download':<10} {'fetch_t':<10} {'pf_dl':<10} {'pf_bc':<10}")
        for r in range(len(accs)):
            acc = accs[r] if r < len(accs) else 0
            loss = losses[r] if r < len(losses) else 0
            rt = real_times[r] if r < len(real_times) else 0
            st = sim_times[r] if r < len(sim_times) else 0
            rct = real_cpu_times[r] if r < len(real_cpu_times) else 0
            comm = comms[r]/(1024*1024) if r < len(comms) else 0
            up = upload_costs[r]/(1024*1024) if r < len(upload_costs) else 0
            dl = download_costs[r]/(1024*1024) if r < len(download_costs) else 0
            ft = fetch_times[r] if r < len(fetch_times) else 0
            pfd = pf_download[r]/(1024*1024) if r < len(pf_download) else 0
            pfb = pf_broadcast[r]/(1024*1024) if r < len(pf_broadcast) else 0
            print(f"  {r+1:<3} {acc:<7.2f} {loss:<8.4f} {rt:<10.2f} {st:<10.2f} {rct:<10.2f} {comm:<10.2f} {up:<10.2f} {dl:<10.2f} {ft:<10.2f} {pfd:<10.2f} {pfb:<10.2f}")
        
        print(f"\n  Summary:")
        print(f"    Total real_time: {sum(real_times):.2f}s")
        print(f"    Total sim_time: {sum(sim_times):.2f}s" if sim_times else "    Total sim_time: N/A")
        print(f"    Total real_cpu: {sum(real_cpu_times):.2f}s" if real_cpu_times else "    Total real_cpu: N/A")
        print(f"    Total comm: {sum(comms)/(1024*1024):.2f} MB")
        print(f"    Total upload: {sum(upload_costs)/(1024*1024):.2f} MB")
        print(f"    Total download: {sum(download_costs)/(1024*1024):.2f} MB")
        print(f"    Total prefetch_download: {sum(pf_download)/(1024*1024):.2f} MB" if pf_download else "    Total prefetch_download: N/A")
        print(f"    Total prefetch_broadcast: {sum(pf_broadcast)/(1024*1024):.2f} MB" if pf_broadcast else "    Total prefetch_broadcast: N/A")
    
    # Read EMA from log
    if os.path.exists(log_path):
        ema_lines = []
        round_dur_lines = []
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'EMA' in line or 'round_duration' in line or 'virtual_clock' in line:
                    ema_lines.append(line.strip())
                if 'round' in line.lower() and ('done' in line.lower() or 'duration' in line.lower()):
                    round_dur_lines.append(line.strip())
        if ema_lines:
            print(f"\n  Log snippets:")
            for line in ema_lines[-15:]:
                print(f"    {line}")
