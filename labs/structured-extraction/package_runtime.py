"""Create a minimal Docker build context from a frozen model and its own code."""
import argparse
import hashlib
import json
import pathlib
import shutil

def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--source',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    out=pathlib.Path(a.out)
    if out.exists():raise ValueError('Use a fresh packaging directory')
    out.mkdir(parents=True);(out/'model').mkdir()
    for name in ['model.onnx','meta.json','lexicon.json']:shutil.copyfile(pathlib.Path(a.bundle)/name,out/'model'/name)
    for name in ['grammar.py','prepare.py','runtime.py','evaluate_cpu.py']:shutil.copyfile(pathlib.Path(a.source)/name,out/name)
    meta=json.loads((pathlib.Path(a.bundle)/'meta.json').read_text())
    if meta.get('grammar_variant')=='money-period-v1':
        shutil.copyfile(pathlib.Path(a.source)/'grammar_robust.py',out/'grammar_robust.py')
    for name in ['Dockerfile','requirements-runtime.txt']:shutil.copyfile(pathlib.Path(__file__).parent/name,out/name)
    receipt={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
    (out/'package-manifest.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))

if __name__=='__main__':main()
