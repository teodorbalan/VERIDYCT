"""ONNX export with the distinct sigmoid decoder, threshold and metadata contract."""
import pathlib
import sys
import torch
import export_cpu
from runtime_multilabel import MultiLabelCpuExtractor,decode_multilabel
from train_multilabel import metrics
from train import read_rows


def export_rows(path):
    rows=read_rows(path)
    for row in rows:
        for candidate in row['candidates']:candidate.pop('labels',None)
    return rows


if __name__=='__main__':
    checkpoint=sys.argv[sys.argv.index('--checkpoint')+1]
    ck=torch.load(checkpoint,map_location='cpu',weights_only=False)
    if ck['meta'].get('decoder')!='multilabel_sigmoid':raise ValueError('Wrong decoder contract')
    threshold=ck['meta']['selected_threshold']
    export_cpu.CpuExtractor=MultiLabelCpuExtractor
    export_cpu.decode=lambda rows,logits,pairs:decode_multilabel(rows,logits,pairs,threshold)
    export_cpu.read_rows=export_rows
    export_cpu.score=metrics
    export_cpu.main()
