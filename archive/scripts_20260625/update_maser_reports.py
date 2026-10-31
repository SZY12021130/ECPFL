"""
更新 MASER report.md 中的通信量数据
假设: 聚合密文大小 = 单个密文大小
"""
import json, glob, os, re

datasets = {
    'MNIST': 'accuracy_baseline/maser/result_fix_pro/experiment_20260621_191848_mnist',
    'FMNIST': 'accuracy_baseline/maser/result_fix_pro/experiment_20260621_200422_fashion_mnist_alpha_1',
}
for p in glob.glob('accuracy_baseline/maser/result_fix_pro/*cifar*/metrics.json'):
    datasets['CIFAR-10'] = os.path.dirname(p)
for p in glob.glob('accuracy_baseline/maser/result_fix_pro/*svhn*/metrics.json'):
    datasets['SVHN'] = os.path.dirname(p)

num_selected = 25

for ds, exp_dir in datasets.items():
    mpath = os.path.join(exp_dir, 'metrics.json')
    rpath = os.path.join(exp_dir, 'report.md')
    
    if not os.path.exists(rpath):
        print(f'{ds}: report.md not found')
        continue
    
    with open(mpath) as f:
        d = json.load(f)
    
    with open(rpath, encoding='utf-8') as f:
        content = f.read()
    
    # 计算修正后的值
    i = 2  # 取稳定轮次
    ct_upload_r = d['maser_ct_upload'][i]
    n_batches = d['num_ciphertexts'][i]
    single_ct_bytes = ct_upload_r / num_selected / n_batches
    
    # 原始总量
    orig_total_ct = sum(d['maser_ct_upload'])
    orig_total_agg = sum(d['maser_agg_ct_download'])
    orig_total_pd = sum(d['maser_partial_dec_upload'])
    orig_total_plain = sum(d['maser_plaintext_download'])
    orig_ul = sum(d['upload_cost'])
    orig_dl = sum(d['download_cost'])
    
    # 修正后总量
    new_total_agg = 0
    new_total_pd = 0
    for j in range(50):
        nb = d['num_ciphertexts'][j]
        new_total_agg += num_selected * nb * single_ct_bytes
        new_total_pd += num_selected * nb * single_ct_bytes
    new_ul = orig_total_ct + new_total_pd
    new_dl = new_total_agg + orig_total_plain
    new_total = new_ul + new_dl
    
    # 原始时间
    orig_ct_ul_time = orig_ct_dl_time = None
    m = re.search(r'CT Upload Time.*?\|\s*([\d.]+)\s*s', content)
    if m: orig_ct_ul_time = float(m.group(1))
    m = re.search(r'CT Download Time.*?\|\s*([\d.]+)\s*s', content)
    if m: orig_ct_dl_time = float(m.group(1))
    
    # 修正后时间
    ratio_ul = new_ul / orig_ul if orig_ul > 0 else 1
    ratio_dl = new_dl / orig_dl if orig_dl > 0 else 1
    new_ct_ul_time = orig_ct_ul_time * ratio_ul if orig_ct_ul_time else 0
    new_ct_dl_time = orig_ct_dl_time * ratio_dl if orig_ct_dl_time else 0
    
    # 计算原始总模拟时间
    orig_total_sim_time = orig_ct_ul_time + orig_ct_dl_time if orig_ct_ul_time and orig_ct_dl_time else 0
    new_total_sim_time = new_ct_ul_time + new_ct_dl_time
    
    # 替换 report.md 中的值
    replacements = [
        # 总通信量
        (r'Total Communication / 总通信量 \| \*\*[\d.]+ MB\*\*',
         f'Total Communication / 总通信量 | **{new_total/1024/1024:.2f} MB**'),
        # 总上传量
        (r'Total Upload / 总上传量 \| [\d.]+ MB / [\d.]+ s',
         f'Total Upload / 总上传量 | {new_ul/1024/1024:.2f} MB / {new_ct_ul_time:.2f} s'),
        # 总下载量
        (r'Total Download / 总下载量 \| [\d.]+ MB / [\d.]+ s',
         f'Total Download / 总下载量 | {new_dl/1024/1024:.2f} MB / {new_ct_dl_time:.2f} s'),
        # MASER ② 聚合密文广播
        (r'MASER ② 聚合密文广播 \| [\d.]+ MB',
         f'MASER ② 聚合密文广播 | {new_total_agg/1024/1024:.2f} MB'),
        # MASER ③ 解密份额上传
        (r'MASER ③ 解密份额上传 \| [\d.]+ MB',
         f'MASER ③ 解密份额上传 | {new_total_pd/1024/1024:.2f} MB'),
        # Avg Upload Cost
        (r'Avg Upload Cost / 平均上传开销 \| [\d.]+ MB',
         f'Avg Upload Cost / 平均上传开销 | {new_ul/50/1024/1024:.2f} MB'),
        # Avg Download Cost
        (r'Avg Download Cost / 平均下载开销 \| [\d.]+ MB',
         f'Avg Download Cost / 平均下载开销 | {new_dl/50/1024/1024:.2f} MB'),
        # CT Upload Time
        (r'CT Upload Time / 密文上传时间 \| [\d.]+ s',
         f'CT Upload Time / 密文上传时间 | {new_ct_ul_time:.2f} s'),
        # CT Download Time
        (r'CT Download Time / 密文下载时间 \| [\d.]+ s',
         f'CT Download Time / 密文下载时间 | {new_ct_dl_time:.2f} s'),
        # Total Simulated Comm Time
        (r'Total Simulated Comm Time / 总模拟通信时间 \| [\d.]+ s',
         f'Total Simulated Comm Time / 总模拟通信时间 | {new_total_sim_time:.2f} s'),
        # Total Simulated Time (需要重新计算)
    ]
    
    # 计算原始总模拟时间（从报告中提取）
    m = re.search(r'Total Simulated Time / 总模拟时间 \| ([\d.]+) s', content)
    if m:
        orig_total_sim = float(m.group(1))
        # 总模拟时间 = 计算时间 + 通信时间
        # 假设计算时间不变，只更新通信时间
        orig_comm_time = orig_ct_ul_time + orig_ct_dl_time if orig_ct_ul_time and orig_ct_dl_time else 0
        calc_time = orig_total_sim - orig_comm_time
        new_total_sim = calc_time + new_total_sim_time
        replacements.append(
            (r'Total Simulated Time / 总模拟时间 \| [\d.]+ s',
             f'Total Simulated Time / 总模拟时间 | {new_total_sim:.2f} s')
        )
    
    # Avg Sim Round Time
    m = re.search(r'Avg Sim Round Time / 平均模拟轮次时间 \| ([\d.]+) s', content)
    if m:
        orig_avg_sim = float(m.group(1))
        new_avg_sim = new_total_sim / 50
        replacements.append(
            (r'Avg Sim Round Time / 平均模拟轮次时间 \| [\d.]+ s',
             f'Avg Sim Round Time / 平均模拟轮次时间 | {new_avg_sim:.2f} s')
        )
    
    # 执行替换
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content)
    
    # 写回文件
    with open(rpath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    orig_total = orig_ul + orig_dl
    print(f'{ds}: report.md updated')
    print(f'  Total Communication: {orig_total/1024/1024:.2f} MB -> {new_total/1024/1024:.2f} MB')
    print(f'  Upload: {orig_ul/1024/1024:.2f} MB -> {new_ul/1024/1024:.2f} MB')
    print(f'  Download: {orig_dl/1024/1024:.2f} MB -> {new_dl/1024/1024:.2f} MB')
    print(f'  CT Upload Time: {orig_ct_ul_time:.2f} s -> {new_ct_ul_time:.2f} s')
    print(f'  CT Download Time: {orig_ct_dl_time:.2f} s -> {new_ct_dl_time:.2f} s')
    print()
