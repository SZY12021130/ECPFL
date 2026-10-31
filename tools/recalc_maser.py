"""
假设 MASER 聚合密文大小 = 单个密文大小，重新计算四个数据集的通信量
"""
import json, glob, os

datasets = {
    'MNIST': 'accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist',
    'FMNIST': 'accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist_alpha_1',
}
for p in glob.glob('accuracy_baseline/maser/result_fix_pro/*cifar*/metrics.json'):
    datasets['CIFAR-10'] = os.path.dirname(p)
for p in glob.glob('accuracy_baseline/maser/result_fix_pro/*svhn*/metrics.json'):
    datasets['SVHN'] = os.path.dirname(p)

num_selected = 25

print("=" * 80)
print("MASER 通信量重新计算 (假设: 聚合密文大小 = 单个密文大小)")
print("=" * 80)

for ds, exp_dir in datasets.items():
    mpath = os.path.join(exp_dir, 'metrics.json')
    with open(mpath) as f:
        d = json.load(f)

    i = 2  # 取稳定轮次(第3轮)
    ct_upload_r = d['maser_ct_upload'][i]
    agg_dl_r = d['maser_agg_ct_download'][i]
    pd_upload_r = d['maser_partial_dec_upload'][i]
    plain_dl_r = d['maser_plaintext_download'][i]
    n_batches = d['num_ciphertexts'][i]

    # 反推单个密文大小
    single_ct_bytes = ct_upload_r / num_selected / n_batches
    single_ct_mb = single_ct_bytes / 1024 / 1024
    orig_agg_ct_mb = agg_dl_r / num_selected / n_batches / 1024 / 1024

    # 50轮原始总量
    orig_total_ct = sum(d['maser_ct_upload'])
    orig_total_agg = sum(d['maser_agg_ct_download'])
    orig_total_pd = sum(d['maser_partial_dec_upload'])
    orig_total_plain = sum(d['maser_plaintext_download'])
    orig_ul = sum(d['upload_cost'])
    orig_dl = sum(d['download_cost'])

    # 新计算: 聚合密文大小 = 单个密文大小
    new_total_agg = 0
    new_total_pd = 0
    for j in range(50):
        nb = d['num_ciphertexts'][j]
        new_total_agg += num_selected * nb * single_ct_bytes
        new_total_pd += num_selected * nb * single_ct_bytes
    new_ul = orig_total_ct + new_total_pd
    new_dl = new_total_agg + orig_total_plain

    print(f"\n{'='*60}")
    print(f"  {ds}")
    print(f"{'='*60}")
    print(f"  单个密文大小: {single_ct_mb:.2f} MB")
    print(f"  原聚合密文大小: {orig_agg_ct_mb:.2f} MB")
    print(f"  压缩比: {orig_agg_ct_mb/single_ct_mb:.1f}x")
    print()
    print(f"  {'项目':<20} {'原始(MB)':>12} {'修正后(MB)':>12} {'原始(GB)':>12} {'修正后(GB)':>12}")
    print(f"  {'-'*70}")
    
    items = [
        ("① 加密上传", orig_total_ct, orig_total_ct),
        ("② 聚合密文广播", orig_total_agg, new_total_agg),
        ("③ 解密份额上传", orig_total_pd, new_total_pd),
        ("④ 明文模型下发", orig_total_plain, orig_total_plain),
        ("Upload(①+③)", orig_ul, new_ul),
        ("Download(②+④)", orig_dl, new_dl),
        ("Total", orig_ul + orig_dl, new_ul + new_dl),
    ]
    for name, orig, new in items:
        print(f"  {name:<20} {orig/1024/1024:>12.2f} {new/1024/1024:>12.2f} {orig/1024/1024/1024:>12.2f} {new/1024/1024/1024:>12.2f}")

    # 通信时间估算
    # 原始时间
    rpath = os.path.join(exp_dir, 'report.md')
    ct_ul_time = None
    ct_dl_time = None
    if os.path.exists(rpath):
        with open(rpath) as f:
            for line in f:
                if 'CT Upload Time' in line and 's' in line:
                    try:
                        ct_ul_time = float(line.split('|')[-2].strip().split()[0])
                    except:
                        pass
                if 'CT Download Time' in line and 's' in line:
                    try:
                        ct_dl_time = float(line.split('|')[-2].strip().split()[0])
                    except:
                        pass

    if ct_ul_time and ct_dl_time:
        # 通信时间正比于通信量
        # 新时间 = 原时间 * (新通信量 / 原通信量)
        # Upload 中 ③ 占主导，Download 中 ② 占主导
        ratio_ul = new_ul / orig_ul if orig_ul > 0 else 1
        ratio_dl = new_dl / orig_dl if orig_dl > 0 else 1
        new_ct_ul_time = ct_ul_time * ratio_ul
        new_ct_dl_time = ct_dl_time * ratio_dl
        
        print()
        print(f"  通信时间:")
        print(f"    CT Upload Time:   原始 {ct_ul_time:.2f} s -> 修正 {new_ct_ul_time:.2f} s")
        print(f"    CT Download Time: 原始 {ct_dl_time:.2f} s -> 修正 {new_ct_dl_time:.2f} s")

print()
