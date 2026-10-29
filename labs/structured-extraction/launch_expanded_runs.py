"""Launch the two explicitly assigned controlled training jobs after preparation."""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--expanded-gpu', type=int, default=4)
    p.add_argument('--control-gpu', type=int, default=5)
    a = p.parse_args()
    root = pathlib.Path(a.root).resolve()
    experiment = root / 'v3-audit/expanded'
    receipt = experiment / 'launches.json'
    if receipt.exists():
        raise ValueError('Launch receipt already exists; do not duplicate jobs')
    launches = []
    deadline = time.monotonic() + 3600
    for mode, gpu in [('expanded', a.expanded_gpu), ('family_control', a.control_gpu)]:
        data = experiment / 'data-v1' / mode
        while not (data / 'preparation.json').exists():
            if time.monotonic() > deadline:
                raise TimeoutError('Preparation did not complete')
            time.sleep(5)
        out = experiment / 'runs' / (mode + '-s271828')
        out.parent.mkdir(exist_ok=True)
        log = experiment / (mode + '-training.log')
        command = [str(root / 'venv/bin/python'), str(experiment / 'source/train_factorized.py'),
                   '--data', str(data), '--out', str(out), '--variant', 'factorized',
                   '--seed', '271828', '--epochs', '40', '--patience', '8', '--batch', '48', '--lr', '.001']
        env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu), OMP_NUM_THREADS='4', MKL_NUM_THREADS='4')
        with log.open('wb') as f:
            proc = subprocess.Popen(command, cwd=experiment / 'source', env=env,
                                    stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
        launches.append(dict(mode=mode, gpu=gpu, pid=proc.pid, command=command,
                             meta_sha256=hashlib.sha256((data / 'meta.json').read_bytes()).hexdigest(),
                             protocol_sha256=hashlib.sha256((data.parent / 'protocol.json').read_bytes()).hexdigest(),
                             selection='unchanged common development mean; family diagnostic excluded from checkpoint selection'))
        receipt.write_text(json.dumps(launches, indent=2) + '\n')
        print(json.dumps(launches[-1]), flush=True)


if __name__ == '__main__':
    main()
