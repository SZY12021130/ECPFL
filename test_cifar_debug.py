import sys
sys.path.insert(0, 'E:\\GithubProjects\\ckks_fed_robustness')
from main import CKKSFedPrefetchExperiment

# Test 1: with global_mask_vote disabled (should work)
print("=" * 60)
print("TEST 1: global_mask_vote = none (baseline)")
print("=" * 60)
experiment = CKKSFedPrefetchExperiment("configs/test_cifar_debug.yaml")
results = experiment.run_experiment_prefetch()
for r in results['results']:
    print(f"Round {r['round']:2d}: test_acc={r['test_acc']:.2f}%")
