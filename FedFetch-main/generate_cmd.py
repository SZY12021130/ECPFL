import yaml
import sys

with open('benchmark/configs/perf/femnist/STC_prefetch.yml') as f:
    data = yaml.safe_load(f)

job_conf = {}
for conf in data['job_conf']:
    job_conf.update(conf)

conf_script = ''
for k, v in job_conf.items():
    conf_script += f' --{k} {v}'

cmd = f"python {data['exp_path']}/{data['aggregator_entry']}{conf_script} --this_rank=0 --num_executors=6 --executor_configs=localhost:[6]"
print(cmd)
