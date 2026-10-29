"""Detached CPU export/cross-evaluation for the three predeclared completed runs."""
import argparse
import json
import os
import pathlib
import subprocess
import time


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--python',required=True)
    a=p.parse_args();root=pathlib.Path(a.root);source=root/'source-million-training-v2'
    jobs=json.loads((root/'million-paired-training-launch-r2.json').read_text())
    state={'phase':'waiting_for_training','exports':{},'scope':'CPU flat extraction only'}
    status=root/'million-postprocess-status.json'
    def save():
        state['updated_unix']=time.time();status.write_text(json.dumps(state,indent=2))
    save()
    while len(state['exports'])<3:
        for job in jobs:
            name=job['name'];view='base' if '-base-' in name else 'v1' if '-v1-' in name else 'v2'
            if view in state['exports']:continue
            run=root/name;result=run/'result.json'
            if not result.exists():
                try:os.kill(job['pid'],0)
                except ProcessLookupError:raise RuntimeError(f'Training exited without result: {name}')
                continue
            json.loads(result.read_text())
            bundle=root/'bundles'/name
            if not (bundle/'export-report.json').exists():
                data=root/'million-paired-base-control' if view=='base' else root/'million-paired-idonly-final'/view
                state['phase']='exporting_'+view;save()
                with (root/f'million-export-{view}-r2.log').open('x') as log:
                    subprocess.run([a.python,str(source/'export_factorized.py'),'--checkpoint',str(run/'best.pt'),
                                    '--data',str(data),'--out',str(bundle)],stdout=log,stderr=subprocess.STDOUT,check=True)
            state['exports'][view]=str(bundle);save()
        if len(state['exports'])<3:time.sleep(10)
    state['phase']='cross_evaluating';save()
    with (root/'million-cross-evaluation-r2.log').open('x') as log:
        subprocess.run([a.python,str(source/'evaluate_million_pair.py'),'--data',str(root/'million-paired-idonly-final'),
                        '--base-bundle',state['exports']['base'],'--v1-bundle',state['exports']['v1'],
                        '--v2-bundle',state['exports']['v2'],'--out',str(root/'million-paired-cross-evaluation-r2')],
                       stdout=log,stderr=subprocess.STDOUT,check=True)
    state['phase']='complete';save()


if __name__=='__main__':main()
