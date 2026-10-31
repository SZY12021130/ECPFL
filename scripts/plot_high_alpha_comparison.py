#!/usr/bin/env python3
"""
High-alpha (α=5,10) experiment comparison chart
Includes CIFAR-10 mutual vs non-mutual, and cross-dataset comparison
"""

import matplotlib.pyplot as plt
import numpy as np
import os

# Ensure Chinese font support
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

# Output directory
os.makedirs('accuracy_niid/plots', exist_ok=True)

# ==================== DATA ====================

# CIFAR-10 data (both mutual and non-mutual)
cifar10_data = {
    'alpha': [0.5, 1.0, 5.0, 10.0],
    'mutual': [74.76, 76.83, 76.89, 77.32],      # avg of 76.91 and 76.87 for alpha=5
    'non_mutual': [None, None, 77.44, 76.76],    # only alpha=5,10 have non-mutual
}

# MNIST data (non-mutual only)
mnist_data = {
    'alpha': [5.0, 10.0],
    'non_mutual': [98.86, 98.86],
}

# Fashion-MNIST data (non-mutual only)
fmnist_data = {
    'alpha': [5.0, 10.0],
    'non_mutual': [89.95, 89.28],
}

# ==================== CHART 1: CIFAR-10 Mutual vs Non-Mutual ====================

fig, ax = plt.subplots(figsize=(10, 6))

alphas = np.array(cifar10_data['alpha'])
mutual = np.array(cifar10_data['mutual'])
non_mutual = np.array([v if v is not None else np.nan for v in cifar10_data['non_mutual']])

width = 0.35
x = np.arange(len(alphas))

bars1 = ax.bar(x - width/2, mutual, width, label='Mutual (互斥)', color='#4472C4', edgecolor='black', linewidth=0.5)
bars2 = ax.bar(x + width/2, non_mutual, width, label='Non-Mutual (非互斥)', color='#ED7D31', edgecolor='black', linewidth=0.5)

# Add value labels on bars
for bar in bars1:
    height = bar.get_height()
    ax.annotate(f'{height:.2f}%',
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points",
                ha='center', va='bottom', fontsize=9)

for bar in bars2:
    height = bar.get_height()
    if not np.isnan(height):
        ax.annotate(f'{height:.2f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)

# Compute and annotate differences for alpha=5,10
for i, alpha in enumerate(alphas):
    if alpha >= 5 and not np.isnan(non_mutual[i]):
        diff = non_mutual[i] - mutual[i]
        color = 'green' if diff > 0 else 'red'
        sign = '+' if diff > 0 else ''
        ax.annotate(f'{sign}{diff:.2f}%',
                    xy=(x[i], max(mutual[i], non_mutual[i]) + 1.5),
                    ha='center', va='bottom', fontsize=10, fontweight='bold', color=color)

ax.set_xlabel('Dirichlet Alpha (α)', fontsize=12)
ax.set_ylabel('Test Accuracy (%)', fontsize=12)
ax.set_title('CIFAR-10: Mutual vs Non-Mutual Decay Mode\n(Sparsity=0.5, 50 rounds)', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels([str(a) for a in alphas])
ax.legend(fontsize=11)
ax.set_ylim(70, 80)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('accuracy_niid/plots/cifar10_mutual_vs_nonmutual_all_alpha.png', dpi=200, bbox_inches='tight')
plt.close()
print("Saved: accuracy_niid/plots/cifar10_mutual_vs_nonmutual_all_alpha.png")

# ==================== CHART 2: Cross-Dataset Comparison (α=5,10) ====================

fig, ax = plt.subplots(figsize=(10, 6))

alphas_high = [5.0, 10.0]
x = np.arange(len(alphas_high))
width = 0.25

# CIFAR-10 (using non-mutual for fair comparison, or mutual where non-mutual unavailable)
cifar10_a5 = 77.44   # non-mutual
cifar10_a10 = 76.76  # non-mutual

mnist_a5 = 98.86
mnist_a10 = 98.86

fmnist_a5 = 89.95
fmnist_a10 = 89.28

bars1 = ax.bar(x - width, [cifar10_a5, cifar10_a10], width, label='CIFAR-10', color='#4472C4', edgecolor='black', linewidth=0.5)
bars2 = ax.bar(x, [mnist_a5, mnist_a10], width, label='MNIST', color='#70AD47', edgecolor='black', linewidth=0.5)
bars3 = ax.bar(x + width, [fmnist_a5, fmnist_a10], width, label='Fashion-MNIST', color='#ED7D31', edgecolor='black', linewidth=0.5)

for bars in [bars1, bars2, bars3]:
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.2f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=9)

ax.set_xlabel('Dirichlet Alpha (α)', fontsize=12)
ax.set_ylabel('Test Accuracy (%)', fontsize=12)
ax.set_title('Cross-Dataset Comparison: High Alpha (α=5, 10)\n(Non-IID, Sparsity=0.5, 50 rounds)', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(['α=5', 'α=10'])
ax.legend(fontsize=11)
ax.set_ylim(70, 102)
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('accuracy_niid/plots/cross_dataset_high_alpha.png', dpi=200, bbox_inches='tight')
plt.close()
print("Saved: accuracy_niid/plots/cross_dataset_high_alpha.png")

# ==================== CHART 3: Alpha Trend per Dataset ====================

fig, axes = plt.subplots(1, 3, figsize=(15, 5))

# CIFAR-10 - mutual mode trend
cifar10_alphas = [0.5, 1.0, 5.0, 10.0]
cifar10_mutual_acc = [74.76, 76.83, 76.89, 77.32]
cifar10_nonmutual_acc = [None, None, 77.44, 76.76]

axes[0].plot(cifar10_alphas, cifar10_mutual_acc, 'o-', color='#4472C4', linewidth=2, markersize=8, label='Mutual')
axes[0].plot([5.0, 10.0], [77.44, 76.76], 's--', color='#ED7D31', linewidth=2, markersize=8, label='Non-Mutual')
for i, (a, acc) in enumerate(zip(cifar10_alphas, cifar10_mutual_acc)):
    axes[0].annotate(f'{acc:.2f}%', (a, acc), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=8)
axes[0].set_title('CIFAR-10', fontsize=12, fontweight='bold')
axes[0].set_xlabel('Alpha (α)')
axes[0].set_ylabel('Accuracy (%)')
axes[0].set_ylim(72, 79)
axes[0].grid(alpha=0.3)
axes[0].legend(fontsize=9)

# MNIST
mnist_alphas = [5.0, 10.0]
mnist_acc = [98.86, 98.86]
axes[1].plot(mnist_alphas, mnist_acc, 'o-', color='#70AD47', linewidth=2, markersize=8)
for a, acc in zip(mnist_alphas, mnist_acc):
    axes[1].annotate(f'{acc:.2f}%', (a, acc), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=9)
axes[1].set_title('MNIST', fontsize=12, fontweight='bold')
axes[1].set_xlabel('Alpha (α)')
axes[1].set_ylim(98, 99.5)
axes[1].grid(alpha=0.3)

# Fashion-MNIST
fmnist_alphas = [5.0, 10.0]
fmnist_acc = [89.95, 89.28]
axes[2].plot(fmnist_alphas, fmnist_acc, 'o-', color='#ED7D31', linewidth=2, markersize=8)
for a, acc in zip(fmnist_alphas, fmnist_acc):
    axes[2].annotate(f'{acc:.2f}%', (a, acc), textcoords="offset points", xytext=(0, 10), ha='center', fontsize=9)
axes[2].set_title('Fashion-MNIST', fontsize=12, fontweight='bold')
axes[2].set_xlabel('Alpha (α)')
axes[2].set_ylim(88, 91)
axes[2].grid(alpha=0.3)

fig.suptitle('Accuracy vs Dirichlet Alpha (Non-IID, Sparsity=0.5)', fontsize=14, fontweight='bold', y=1.02)
plt.tight_layout()
plt.savefig('accuracy_niid/plots/alpha_trend_per_dataset.png', dpi=200, bbox_inches='tight')
plt.close()
print("Saved: accuracy_niid/plots/alpha_trend_per_dataset.png")

# ==================== SUMMARY TABLE ====================
print("\n" + "="*70)
print("HIGH-ALPHA EXPERIMENT RESULTS SUMMARY")
print("="*70)
print(f"{'Dataset':<15} {'Alpha':<8} {'Mode':<14} {'Accuracy':<10}")
print("-"*70)
print(f"{'CIFAR-10':<15} {'0.5':<8} {'Mutual':<14} {'74.76%':<10}")
print(f"{'CIFAR-10':<15} {'1.0':<8} {'Mutual':<14} {'76.83%':<10}")
print(f"{'CIFAR-10':<15} {'5':<8} {'Mutual':<14} {'76.89%':<10}")
print(f"{'CIFAR-10':<15} {'5':<8} {'Non-Mutual':<14} {'77.44%':<10}  (+0.55%)")
print(f"{'CIFAR-10':<15} {'10':<8} {'Mutual':<14} {'77.32%':<10}")
print(f"{'CIFAR-10':<15} {'10':<8} {'Non-Mutual':<14} {'76.76%':<10}  (-0.56%)")
print(f"{'MNIST':<15} {'5':<8} {'Non-Mutual':<14} {'98.86%':<10}")
print(f"{'MNIST':<15} {'10':<8} {'Non-Mutual':<14} {'98.86%':<10}")
print(f"{'Fashion-MNIST':<15} {'5':<8} {'Non-Mutual':<14} {'89.95%':<10}")
print(f"{'Fashion-MNIST':<15} {'10':<8} {'Non-Mutual':<14} {'89.28%':<10}")
print("="*70)
print("\nKey Findings:")
print("  1. CIFAR-10 α=5:  Non-mutual slightly better (+0.55%)")
print("  2. CIFAR-10 α=10: Mutual slightly better (+0.56%)")
print("  3. High alpha (≥5) mutual vs non-mutual diff: < 0.6% (negligible)")
print("  4. MNIST:   Perfect stability at 98.86% for both α=5 and α=10")
print("  5. F-MNIST: Slight drop from 89.95% (α=5) to 89.28% (α=10)")
print("="*70)
