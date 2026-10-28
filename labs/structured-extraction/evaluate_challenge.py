"""Evaluate an explicitly selected JSONL challenge with its frozen CPU bundle.

Final fixtures require --allow-final after selection freeze. This is a guard,
not cryptographic isolation: governance must keep final outputs out of tuning.
"""
import argparse
import collections
import hashlib
import json
import pathlib
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--allow-final", action="store_true")
    parser.add_argument("--batch", type=int, default=32)
    args = parser.parse_args()
    fixture, out = pathlib.Path(args.fixture), pathlib.Path(args.out)
    if "final" in fixture.name and not args.allow_final:
        raise ValueError("Final challenge is reserved until model selection freeze")
    if out.exists():
        raise ValueError("Use a fresh output directory")
    out.mkdir(parents=True)
    sys.path.insert(0, str(pathlib.Path(args.bundle)))
    from runtime import CpuExtractor, encode_input
    from grammar import canonical
    engine = CpuExtractor(args.bundle)
    rows = [json.loads(x) for x in fixture.open(encoding="utf-8")]
    for row in rows:
        if row.get("split") == "final" and not args.allow_final:
            raise ValueError("Final fixture requires explicit release")
    started = time.monotonic()
    encoded = [dict(encode_input(r["text"], r.get("previous_text", ""), engine.meta, engine.grammar, r["id"]), original=r) for r in rows]
    encoded.sort(key=lambda r: len(r["tokens"]))
    stats = collections.defaultdict(collections.Counter)
    coverage = collections.Counter()
    predictions = []
    key = lambda a: (a["subject"], a["attribute"], canonical(a["value"]))
    for i in range(0, len(encoded), args.batch):
        selected = encoded[i:i + args.batch]
        for r, pred in zip(selected, engine.predict_encoded(selected)):
            row = r["original"]
            g, p = {key(a) for a in row["form"]}, {key(a["atom"]) for a in pred}
            if not row.get("ambiguous") and not row.get("diagnostic"):
                values = {canonical(c["value"]) for c in r["candidates"]}
                gold_values = [canonical(a["value"]) for a in row["form"]]
                coverage.update(rows=1, positive_rows=bool(gold_values), gold_atoms=len(gold_values),
                                covered_atoms=sum(v in values for v in gold_values),
                                all_values_covered=all(v in values for v in gold_values))
            scope = "ambiguity_only" if row.get("ambiguous") else "type_diagnostic" if row.get("diagnostic") else "primary"
            groups = [row["category"], scope]
            for group in groups:
                stats[group].update(rows=1, exact=g == p, gold=len(g), predicted=len(p), correct=len(g & p))
            predictions.append(dict(row, prediction=pred, exact=g == p))
    for group in stats.values():
        group["exact_rate"] = group["exact"] / group["rows"]
        group["f1"] = 2 * group["correct"] / max(1, group["gold"] + group["predicted"])
    report = {"groups": dict(stats), "candidate_value_coverage": dict(coverage), "seconds": time.monotonic() - started,
              "fixture_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
              "model_sha256": hashlib.sha256((pathlib.Path(args.bundle) / "model.onnx").read_bytes()).hexdigest(),
              "scope": "Assistant-authored closed-ontology behavior challenge; not official contest score; ambiguity abstention kept separate"}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    (out / "predictions.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in predictions))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
