"""After training finishes, export once and evaluate only declared development data."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    a = p.parse_args()
    root = pathlib.Path(a.root).resolve()
    exp = root / 'v3-audit/expanded'
    source = exp / 'export-source'
    python = root / 'venv/bin/python'
    receipt = exp / 'completion-receipts.json'
    if receipt.exists():
        raise ValueError('Completion receipt exists; inspect it before any retry')
    records = []
    deadline = time.monotonic() + 7200
    for mode in ['family_control', 'expanded']:
        run = exp / 'runs' / (mode + '-s271828')
        while not (run / 'result.json').exists():
            if time.monotonic() > deadline:
                raise TimeoutError('Training has not completed')
            time.sleep(10)
        bundle = exp / 'bundles' / (mode + '-s271828-v1')
        command = [str(python), str(source / 'export_factorized.py'), '--checkpoint', str(run / 'best.pt'),
                   '--data', str(exp / 'data-v1' / mode), '--out', str(bundle)]
        with (exp / (mode + '-export.log')).open('w') as f:
            result = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, cwd=source)
        record = dict(mode=mode, export_command=command, export_exit_code=result.returncode)
        if result.returncode:
            records.append(record); receipt.write_text(json.dumps(records, indent=2)); continue
        # Always re-encode the same raw family diagnostic with this model's own
        # train-only vocabulary; no model sees the other's token IDs.
        sys.path.insert(0, str(source))
        from runtime import CpuExtractor
        from evaluate_cpu import evaluate
        engine = CpuExtractor(bundle)
        path = exp / 'data-v1/family_control/family-diagnostic.jsonl'
        rows = [json.loads(x) for x in path.open()]
        dest = exp / 'evaluations' / mode
        dest.mkdir(parents=True)
        family = evaluate(engine, rows, dest / 'family-predictions.jsonl')
        family['fixture_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        family['status'] = 'diagnostic only; prior experiments used these families; expanded model trains on them'
        (dest / 'family-report.json').write_text(json.dumps(family, indent=2))
        challenge_command = [str(python), str(source / 'evaluate_challenge.py'), '--bundle', str(bundle),
                             '--fixture', str(root / 'v3-audit/challenge-dev.jsonl'), '--out', str(dest / 'challenge-dev')]
        with (dest / 'challenge.log').open('w') as f:
            result = subprocess.run(challenge_command, stdout=f, stderr=subprocess.STDOUT)
        record.update(bundle=str(bundle), family=family, challenge_exit_code=result.returncode,
                      export=json.loads((bundle / 'export-report.json').read_text()))
        if not result.returncode:
            record['challenge'] = json.loads((dest / 'challenge-dev/report.json').read_text())
        records.append(record)
        receipt.write_text(json.dumps(records, indent=2) + '\n')
        print(json.dumps(dict(mode=mode, family=family['groups']['all'], challenge_exit_code=result.returncode)), flush=True)


if __name__ == '__main__':
    main()
