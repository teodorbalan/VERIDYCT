"""Controlled comparison: identical frozen ONNX weights, period adapter only."""
import argparse
import collections
import hashlib
import json
import pathlib
import sys
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    out = pathlib.Path(args.out)
    if out.exists():
        raise ValueError("Use fresh output directory")
    out.mkdir(parents=True)
    sys.path.insert(0, args.bundle)
    from runtime import CpuExtractor, encode_input
    from grammar import canonical
    from grammar_robust import RobustGrammar
    base = CpuExtractor(args.bundle)
    robust = RobustGrammar(base.lexicon, base.meta["extra_names"])
    data = pathlib.Path(args.data)
    report = {"model_sha256": hashlib.sha256((pathlib.Path(args.bundle) / "model.onnx").read_bytes()).hexdigest(),
              "adapter_sha256": hashlib.sha256(pathlib.Path(__file__).with_name("grammar_robust.py").read_bytes()).hexdigest(),
              "coverage": {}, "metrics": {}, "scope": "Development-only comparison; same model, inputs and logits; normalize monetary per field only. No reserved final gold read."}
    dev = None
    for split in ["train", "dev"]:
        rows = [json.loads(x) for x in (data / f"{split}.jsonl").open()]
        counts = collections.Counter()
        changed = []
        for row in rows:
            a, b = base.grammar.candidates(row["text"]), robust.candidates(row["text"])
            assert len(a) == len(b)
            assert all((x["start"], x["end"], x["value"]["kind"]) == (y["start"], y["end"], y["value"]["kind"]) for x, y in zip(a, b))
            av, bv = {canonical(c["value"]) for c in a}, {canonical(c["value"]) for c in b}
            gold = [canonical(a["value"]) for a in row["form"]]
            counts.update(rows=1, gold_atoms=len(gold), base_covered=sum(v in av for v in gold),
                          robust_covered=sum(v in bv for v in gold), gained_atoms=sum(v not in av and v in bv for v in gold),
                          lost_atoms=sum(v in av and v not in bv for v in gold), changed_rows=a != b)
            if a != b:
                changed.append({"id": row["id"], "text": row["text"], "gold": row["form"], "base_money": [c for c in a if c['value']['kind']=='money'], "robust_money": [c for c in b if c['value']['kind']=='money']})
        report["coverage"][split] = dict(counts)
        (out / f"changed-{split}.json").write_text(json.dumps(changed, indent=2))
        if split == "dev":
            dev = rows
    key = lambda a: (a["subject"], a["attribute"], canonical(a["value"]))
    for variant, grammar in [("baseline", base.grammar), ("period_adapter", robust)]:
        stats = collections.defaultdict(collections.Counter)
        encoded = []
        started = time.monotonic()
        for row in dev:
            encoded.append(dict(encode_input(row["text"], row["previous_text"], base.meta, grammar, row["id"]), gold=row["form"], domain=row["domain"]))
        encoded.sort(key=lambda r: len(r["tokens"]))
        preds = []
        for i in range(0, len(encoded), 48):
            selected = encoded[i:i + 48]
            for row, prediction in zip(selected, base.predict_encoded(selected)):
                g, a = {key(v) for v in row["gold"]}, {key(v["atom"]) for v in prediction}
                for domain in [row["domain"], "all"]:
                    stats[domain].update(rows=1, exact=g == a, gold=len(g), predicted=len(a), correct=len(g & a))
                preds.append({"id": row["id"], "prediction": prediction})
        for group in stats.values():
            group["exact_rate"] = group["exact"] / group["rows"]
            group["f1"] = 2 * group["correct"] / (group["gold"] + group["predicted"])
        report["metrics"][variant] = {"groups": dict(stats), "seconds": time.monotonic() - started}
        (out / f"{variant}-predictions.jsonl").write_text("".join(json.dumps(x) + "\n" for x in preds))
    (out / "report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
