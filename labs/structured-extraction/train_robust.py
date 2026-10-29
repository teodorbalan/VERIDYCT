"""Controlled R-Drop experiment; same extractor, data and selection as train.py.

Two dropout samples receive supervised loss and symmetric KL consistency.
Reference: https://arxiv.org/abs/2106.14448. No extra inference parameters.
"""
import argparse
import hashlib
import json
import os
import pathlib
import platform
import random
import time

import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader
from model import Extractor, CONFIGS, collate
from train import read_rows, evaluate


def rdrop_kl(first, second, labels):
    valid = labels.ne(-100)
    p, q = first.log_softmax(-1), second.log_softmax(-1)
    kl = .5*((p.exp()*(p-q)).sum(-1)+(q.exp()*(q-p)).sum(-1))
    return kl[valid].mean()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--family", choices=["baseline", "factorized"], default="baseline")
    p.add_argument("--variant", default="03-char-bilstm")
    p.add_argument("--seed", type=int, default=271828)
    p.add_argument("--alpha", type=float, default=1.)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--patience", type=int, default=8)
    p.add_argument("--batch", type=int, default=48)
    p.add_argument("--lr", type=float, default=.001)
    a = p.parse_args()
    torch.set_num_threads(4)
    torch.set_num_interop_threads(2)
    torch.set_float32_matmul_precision("high")
    random.seed(a.seed)
    np.random.seed(a.seed)
    torch.manual_seed(a.seed)
    if not torch.cuda.is_available():
        raise RuntimeError("This experiment requires a GPU; no silent fallback")
    root, out = pathlib.Path(a.data), pathlib.Path(a.out)
    if out.exists():
        raise ValueError("Use a fresh run directory")
    out.mkdir(parents=True)
    meta = json.loads((root/"meta.json").read_text())
    train, dev = read_rows(root/"train.jsonl"), read_rows(root/"dev.jsonl")
    train.sort(key=lambda r:len(r["tokens"]))
    dev.sort(key=lambda r:len(r["tokens"]))
    loader = DataLoader(train, batch_size=a.batch, shuffle=True, collate_fn=collate,
                        num_workers=2, persistent_workers=True)
    validation = DataLoader(dev, batch_size=a.batch, collate_fn=collate,
                            num_workers=2, persistent_workers=True)
    schema = None
    if a.family == "factorized":
        from model_factorized import FactorizedExtractor, make_schema, CONFIGS as FACTORIZED_CONFIGS
        config = FACTORIZED_CONFIGS[a.variant]
        schema = make_schema(meta, train, json.loads((root/"lexicon.json").read_text()))
        model = FactorizedExtractor(len(meta["vocab"]), len(meta["chars"]), len(meta["pairs"]), config, schema).cuda()
    else:
        config = CONFIGS[a.variant]
        model = Extractor(len(meta["vocab"]), len(meta["chars"]), len(meta["pairs"]), config).cuda()
    with torch.no_grad():
        model.word.weight.copy_(torch.from_numpy(np.load(root/"vectors.npy")).cuda())
    optimizer = torch.optim.AdamW(model.parameters(), lr=a.lr, weight_decay=.01)
    weights = torch.ones(len(meta["pairs"])+1, device="cuda")
    weights[0] = .25
    info = dict(variant=a.variant, family=a.family, experiment="rdrop", alpha=a.alpha, seed=a.seed,
                parameters=sum(x.numel() for x in model.parameters()), config=config,
                torch=torch.__version__, python=platform.python_version(),
                gpu=torch.cuda.get_device_name(), cuda_visible_devices=os.getenv("CUDA_VISIBLE_DEVICES"),
                train_rows=len(train), dev_rows=len(dev), arguments=vars(a),
                data_sha256=hashlib.sha256((root/"meta.json").read_bytes()).hexdigest(),
                source_sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest()
                               for f in pathlib.Path(__file__).parent.glob("*.py")})
    (out/"run.json").write_text(json.dumps(info, indent=2))
    print(json.dumps(info), flush=True)
    started = time.monotonic()
    best, stale = -1, 0
    for epoch in range(a.epochs):
        model.train()
        t0, loss_total = time.monotonic(), 0.
        for inputs, labels, _ in loader:
            inputs = [x.cuda() for x in inputs]
            labels = labels.cuda()
            optimizer.zero_grad(set_to_none=True)
            first = model(*inputs)
            second = model(*inputs)
            ce = .5*(F.cross_entropy(first.flatten(0,1), labels.flatten(), weight=weights, ignore_index=-100)
                      + F.cross_entropy(second.flatten(0,1), labels.flatten(), weight=weights, ignore_index=-100))
            loss = ce+a.alpha*rdrop_kl(first, second, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.)
            optimizer.step()
            loss_total += float(loss.detach())
        elapsed = time.monotonic()-t0
        metrics = evaluate(model, validation, "cuda", meta["pairs"])
        rec = dict(epoch=epoch+1, loss=loss_total/len(loader), train_seconds=elapsed,
                   dev=metrics, elapsed_seconds=time.monotonic()-started,
                   gpu_peak_mib=torch.cuda.max_memory_allocated()/2**20)
        with (out/"metrics.jsonl").open("a") as f:
            f.write(json.dumps(rec)+"\n")
        print(json.dumps(rec), flush=True)
        improved = metrics["selection_score"]>best
        if improved:
            best, stale = metrics["selection_score"], 0
        else:
            stale += 1
        ck = dict(model=model.state_dict(), optimizer=optimizer.state_dict(), epoch=epoch+1,
                  best=best, config=config, meta=meta, metrics=metrics, experiment=info)
        if schema is not None:
            ck["schema"] = schema
        torch.save(ck, out/"last.tmp")
        os.replace(out/"last.tmp", out/"last.pt")
        if improved:
            torch.save(ck, out/"best.tmp")
            os.replace(out/"best.tmp", out/"best.pt")
        if stale>=a.patience:
            break
    ck = torch.load(out/"best.pt", map_location="cuda", weights_only=False)
    model.load_state_dict(ck["model"])
    result = evaluate(model, validation, "cuda", meta["pairs"], out/"dev-predictions.jsonl")
    result.update(best_epoch=ck["epoch"], total_seconds=time.monotonic()-started,
                  variant=a.variant, parameters=info["parameters"], experiment="rdrop")
    (out/"result.json").write_text(json.dumps(result, indent=2))
    print("COMPLETE "+json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
