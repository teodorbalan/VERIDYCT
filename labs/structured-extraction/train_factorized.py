"""Controlled training on the unchanged prepared split; separate run directories."""
import argparse
import hashlib
import json
import os
import pathlib
import random
import time
import numpy as np
import torch
from torch.utils.data import DataLoader
from model import collate
from model_factorized import CONFIGS, FactorizedExtractor, make_schema
from train import read_rows, evaluate


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data', required=True); p.add_argument('--out', required=True)
    p.add_argument('--variant', choices=CONFIGS, required=True)
    p.add_argument('--seed', type=int, default=271828)
    p.add_argument('--epochs', type=int, default=40)
    p.add_argument('--patience', type=int, default=8)
    p.add_argument('--batch', type=int, default=48)
    p.add_argument('--lr', type=float, default=.001)
    a = p.parse_args()
    torch.set_num_threads(4); torch.set_num_interop_threads(2)
    torch.set_float32_matmul_precision('high')
    random.seed(a.seed); np.random.seed(a.seed); torch.manual_seed(a.seed)
    if not torch.cuda.is_available(): raise RuntimeError('CUDA is required for this training run')
    root = pathlib.Path(a.data); out = pathlib.Path(a.out)
    if out.exists(): raise ValueError('Use a fresh output directory')
    out.mkdir(parents=True)
    meta = json.loads((root/'meta.json').read_text())
    rows = read_rows(root/'train.jsonl'); dev = read_rows(root/'dev.jsonl')
    rows.sort(key=lambda r:len(r['tokens'])); dev.sort(key=lambda r:len(r['tokens']))
    train_loader = DataLoader(rows, batch_size=a.batch, shuffle=True, collate_fn=collate,
                              num_workers=2, persistent_workers=True)
    dev_loader = DataLoader(dev, batch_size=a.batch, collate_fn=collate,
                            num_workers=2, persistent_workers=True)
    schema = make_schema(meta, rows); config = dict(CONFIGS[a.variant])
    model = FactorizedExtractor(len(meta['vocab']), len(meta['chars']), len(meta['pairs']), config, schema).cuda()
    with torch.no_grad(): model.word.weight.copy_(torch.from_numpy(np.load(root/'vectors.npy')).cuda())
    weights = torch.ones(len(meta['pairs'])+1, device='cuda'); weights[0] = .25
    criterion = torch.nn.CrossEntropyLoss(weight=weights, ignore_index=-100)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=.01)
    info = dict(arguments=vars(a), parameters=sum(p.numel() for p in model.parameters()),
                torch=torch.__version__, gpu=torch.cuda.get_device_name(),
                cuda_visible_devices=os.environ.get('CUDA_VISIBLE_DEVICES'),
                data_sha256=hashlib.sha256((root/'meta.json').read_bytes()).hexdigest(),
                source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in pathlib.Path(__file__).parent.glob('*.py')},
                kind_prior='soft penalty from training observed kinds, not an authoritative schema')
    (out/'run.json').write_text(json.dumps(info, indent=2)); print(json.dumps(info), flush=True)
    best = -1; stale = 0; start = time.monotonic()
    for epoch in range(a.epochs):
        model.train(); loss_total = 0; epoch_start = time.monotonic()
        for inputs, labels, _ in train_loader:
            opt.zero_grad(set_to_none=True)
            logits = model(*(x.cuda() for x in inputs))
            loss = criterion(logits.reshape(-1, logits.shape[-1]), labels.cuda().flatten())
            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); opt.step()
            loss_total += loss.item()
        train_seconds = time.monotonic()-epoch_start
        metrics = evaluate(model, dev_loader, 'cuda', meta['pairs'])
        record = dict(epoch=epoch+1, loss=loss_total/len(train_loader),
                      train_seconds=train_seconds, dev=metrics,
                      elapsed_seconds=time.monotonic()-start,
                      gpu_peak_mib=torch.cuda.max_memory_allocated()/2**20)
        with (out/'metrics.jsonl').open('a') as f: f.write(json.dumps(record)+'\n')
        print(json.dumps(record), flush=True)
        improved = metrics['selection_score'] > best
        if improved: best=metrics['selection_score']; stale=0
        else: stale += 1
        ck = dict(model=model.state_dict(), optimizer=opt.state_dict(), epoch=epoch+1,
                  config=config, schema=schema, meta=meta, metrics=metrics, best=best)
        torch.save(ck, out/'last.tmp'); os.replace(out/'last.tmp', out/'last.pt')
        if improved:
            torch.save(ck, out/'best.tmp'); os.replace(out/'best.tmp', out/'best.pt')
        if stale >= a.patience: break
    ck=torch.load(out/'best.pt', map_location='cuda', weights_only=False)
    model.load_state_dict(ck['model'])
    result=evaluate(model, dev_loader, 'cuda', meta['pairs'], out/'dev-predictions.jsonl')
    result.update(best_epoch=ck['epoch'], total_seconds=time.monotonic()-start,
                  parameters=info['parameters'], variant=a.variant, seed=a.seed)
    (out/'result.json').write_text(json.dumps(result,indent=2)); print('COMPLETE '+json.dumps(result),flush=True)


if __name__ == '__main__': main()
