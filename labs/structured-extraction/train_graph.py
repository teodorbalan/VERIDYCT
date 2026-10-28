"""Reuse the frozen optimizer, split and metrics for a controlled label-graph study."""
import argparse
import json
import pathlib
import train as baseline
from model_graph import GraphExtractor, CONFIGS


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--data', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--variant', choices=CONFIGS, required=True)
    p.add_argument('--device', default='cuda')
    p.add_argument('--epochs', type=int, default=40)
    p.add_argument('--patience', type=int, default=8)
    p.add_argument('--batch', type=int, default=48)
    p.add_argument('--lr', type=float, default=.001)
    p.add_argument('--seed', type=int, default=271828)
    p.add_argument('--smoke', action='store_true')
    p.add_argument('--resume', action='store_true')
    p.add_argument('--pretrained', action='store_true')
    args = p.parse_args()
    meta = json.loads((pathlib.Path(args.data) / 'meta.json').read_text())
    baseline.CONFIGS = CONFIGS
    baseline.Extractor = lambda _v, _c, _p, config: GraphExtractor(meta, config)
    baseline.train(args)


if __name__ == '__main__':
    main()
