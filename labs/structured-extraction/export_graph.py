"""Export a graph checkpoint with the same text reconstruction and parity checks."""
import sys
import pathlib
import json
import hashlib
import torch
import export_cpu
from model_graph import load_model, fold_graph_head, GraphExtractor


if __name__ == '__main__':
    torch.set_num_threads(2)
    if '--checkpoint' not in sys.argv:
        raise SystemExit('Use --checkpoint for an individual graph-model export')
    path = sys.argv[sys.argv.index('--checkpoint') + 1]
    original, ck = load_model(path)
    if len(original.candidate_blocks):
        # The candidate graph depends on input clauses and cannot be folded away.
        export_cpu.Extractor = lambda _v, _c, _p, config: GraphExtractor(ck['meta'], config)
        export_cpu.main()
        raise SystemExit(0)
    folded = fold_graph_head(original, ck['meta'])
    out = pathlib.Path(sys.argv[sys.argv.index('--out') + 1])
    out.mkdir(parents=True, exist_ok=True)
    folded_path = out / 'folded.pt'
    if folded_path.exists():
        raise SystemExit('Refusing to overwrite an existing folded checkpoint')
    deployment = {k: v for k, v in ck.items() if k != 'optimizer'}
    torch.save(dict(deployment, model=folded.state_dict(), config=folded.config), folded_path)
    # Verify the algebraic head fold on diverse real development shapes before ONNX.
    root = pathlib.Path(sys.argv[sys.argv.index('--data') + 1])
    from train import read_rows
    from model import collate
    rows = read_rows(root / 'dev.jsonl')
    rows.sort(key=lambda r: len(r['tokens']))
    errors = []
    with torch.no_grad():
        for selected in [rows[:1], rows[100:107], rows[-32:]]:
            inp = collate(selected)[0]
            a = original(*inp)
            b = folded(*inp)
            error = float((a - b).abs().max())
            errors.append(error)
            torch.testing.assert_close(a, b, atol=2e-4, rtol=2e-5)
    (out / 'fold-report.json').write_text(json.dumps({
        'source_checkpoint_sha256': hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest(),
        'source_parameters': sum(p.numel() for p in original.parameters()),
        'folded_parameters': sum(p.numel() for p in folded.parameters()),
        'max_abs_errors': errors,
        'operation': 'exact static label graph + direct linear head folding'}, indent=2))
    sys.argv[sys.argv.index('--checkpoint') + 1] = str(folded_path)
    export_cpu.main()
