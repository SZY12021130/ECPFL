import sys, json
sys.path.insert(0, 'E:\\GithubProjects\\ckks_fed_robustness')
from main import CKKSFedPrefetchExperiment

experiment = CKKSFedPrefetchExperiment("configs/test_pf2_tee_nores.yaml")
results = experiment.run_experiment_prefetch()

print("\n=== Prefetch Accuracy ===")
for r in results['results']:
    print(f"Round {r['round']:2d}: test_acc={r['test_acc']:.2f}%")

m = results['metrics']
print(f"\n=== Communication ===")
print(f"Avg Upload: {sum(m.get('upload_cost',[]))/len(m.get('upload_cost',[1]))/1024:.2f} KB")
print(f"Avg Download: {sum(m.get('download_cost',[]))/len(m.get('download_cost',[1]))/1024:.2f} KB")
print(f"Total Comm: {sum(m.get('total_communication_cost',[]))/(1024*1024):.2f} MB")
print(f"Avg Sim Time: {sum(m.get('total_round_time',[]))/len(m.get('total_round_time',[1])):.2f} s")

# Check fetch stats
total_fetch = sum(c.get_prefetch_stats()['fetch_download_cost'] for c in experiment.clients)
total_prefetch = sum(c.get_prefetch_stats()['prefetch_download_cost'] for c in experiment.clients)
print(f"\n=== Prefetch Stats ===")
print(f"Total Prefetch DL: {total_prefetch/1024:.2f} KB")
print(f"Total Fetch DL: {total_fetch/1024:.2f} KB")

if total_fetch > 0:
    print("\nFetch download > 0: PASS")
else:
    print("\nFetch download = 0: may need investigation")

# Save to a temp file for verification
with open('test_pf2_result.json', 'w') as f:
    json.dump({
        'accs': [r['test_acc'] for r in results['results']],
        'total_fetch': total_fetch,
        'total_prefetch': total_prefetch,
        'avg_download': sum(m.get('download_cost',[]))/len(m.get('download_cost',[1])),
    }, f)
