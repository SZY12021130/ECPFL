import os
import re
import glob

strategies = ["random", "sticky", "sketch_clustering", "poc", "tifl", "haccs", "oort"]
datasets = [
    ("MNIST", "mnist_vote_0.1"),
    ("Fashion-MNIST", "fashion_mnist_vote_0.3"),
    ("CIFAR-10", "cifar10_vote_0.7"),
]

def parse_size(s):
    s = s.strip()
    if s.endswith("MB"):
        return float(s[:-2].strip())
    elif s.endswith("KB"):
        return float(s[:-2].strip()) / 1024
    elif s.endswith("B"):
        val = s[:-1].strip()
        if val == "0":
            return 0.0
        return float(val) / (1024 * 1024)
    elif s.endswith("GB"):
        return float(s[:-2].strip()) * 1024
    return 0.0

def parse_log(log_path):
    with open(log_path, 'rb') as f:
        raw = f.read()
    
    total_comm = 0.0
    total_ul = 0.0
    total_dl = 0.0
    
    # Pattern: comm=XX MB (\xa1\xfcYY MB \xa1\xfdZZ B)
    pattern = re.compile(
        rb'comm=([\d.]+\s*(?:MB|KB|B|GB))\s*\('
        rb'(?:\xa1\xfc|\xe2\x86\x91)'
        rb'([\d.]+\s*(?:MB|KB|B|GB))\s*'
        rb'(?:\xa1\xfd|\xe2\x86\x93)'
        rb'([\d.]+\s*(?:MB|KB|B|GB))\)'
    )
    
    for m in pattern.finditer(raw):
        total_comm += parse_size(m.group(1).decode('ascii'))
        total_ul += parse_size(m.group(2).decode('ascii'))
        total_dl += parse_size(m.group(3).decode('ascii'))
    
    actual_comm = 0.0
    summary_start = raw.find(b'SUMMARY')
    summary_part = raw[summary_start:] if summary_start != -1 else raw
    
    for line in summary_part.split(b'\n'):
        line_str = line.decode('utf-8', errors='ignore')
        if 'Client' in line_str and 'Mbps' in line_str:
            sizes = re.findall(r'[\d.]+\s*(?:MB|KB|B|GB)', line_str)
            if sizes:
                actual_comm += parse_size(sizes[-1])
    
    return total_comm, total_ul, total_dl, actual_comm

for ds_label, ds_pattern in datasets:
    for strategy in strategies:
        dirs = glob.glob(f"accuracy_client_selection/*_{ds_pattern}_cs_{strategy}")
        if not dirs:
            continue
        log_path = os.path.join(dirs[0], "run.log")
        if not os.path.exists(log_path):
            continue
        total_comm, total_ul, total_dl, actual_comm = parse_log(log_path)
        print(f"{ds_label} {strategy}: sim={total_comm:.2f}MB, ul={total_ul:.2f}MB, dl={total_dl:.2f}MB, actual={actual_comm:.2f}MB")
