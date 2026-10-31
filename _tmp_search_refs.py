import os
pats = ['ConjugatePacking','TwoTierPacking','conjugate','twotier','two_tier','_check_conjugate','_CONJUGATE_SUPPORTED','two-tier']
skip = {'__pycache__','.git','node_modules','data','results','history_models','visualization','result_fix','result_fix_pro','artifacts','.pytest_cache','venv','env'}
hits = []
for root, dirs, files in os.walk('.'):
    dirs[:] = sorted(d for d in dirs if d not in skip)
    # 跳过 experiment_ 开头的实验目录
    dirs[:] = [d for d in dirs if not d.startswith('experiment_')]
    for f in files:
        if f.startswith('_tmp_'):
            continue
        ext = f.rsplit('.',1)[-1].lower() if '.' in f else ''
        if ext not in ('py','yaml','yml','md','txt','cfg','ini'):
            continue
        p = os.path.join(root, f)
        try:
            for i, line in enumerate(open(p, encoding='utf-8', errors='replace'), 1):
                ll = line.lower()
                for pat in pats:
                    if pat.lower() in ll:
                        hits.append((p, i, pat, line.strip()[:130]))
                        break
        except Exception:
            pass

out = open('_tmp_refs_result.txt', 'w', encoding='utf-8')
out.write('TOTAL HITS: %d\n' % len(hits))
seen = {}
for p, i, pat, l in hits:
    seen.setdefault(p, 0); seen[p] += 1
for p, c in sorted(seen.items()):
    out.write('  %3dx  %s\n' % (c, p))
out.write('\n--- detail ---\n')
for p, i, pat, l in hits:
    out.write('%s:%d [%s] %s\n' % (p, i, pat, l))
out.close()
print('done, hits=', len(hits))
