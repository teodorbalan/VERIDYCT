"""Behavioral probes on existing development rows, never final fixtures."""
import argparse
import collections
import hashlib
import json
import pathlib
import random
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--per-domain", type=int, default=100)
    args = parser.parse_args()
    sys.path.insert(0, args.bundle)
    from runtime import CpuExtractor, encode_input
    from grammar import canonical
    out = pathlib.Path(args.out)
    if out.exists():
        raise ValueError("Use a fresh output file")
    source = pathlib.Path(args.data) / "dev.jsonl"
    population = [json.loads(line) for line in source.open()]
    rng = random.Random(9102026)
    chosen = []
    for domain in ["official", "synthetic"]:
        subset = [row for row in population if row["domain"] == domain]
        chosen.extend(rng.sample(subset, min(args.per_domain, len(subset))))
    engine = CpuExtractor(args.bundle)
    key = lambda a: (a["subject"], a["attribute"], canonical(a["value"]))
    encode = lambda text, prev: encode_input(text, prev, engine.meta, engine.grammar)
    stats = collections.defaultdict(collections.Counter)
    examples = []
    start = time.monotonic()
    filler = encode("The narrator was discussing music and weather. " * 25, "")
    for row in chosen:
        original = encode(row["text"], row["previous_text"])
        baseline = {key(p["atom"]) for p in engine.predict_encoded([original])[0]}
        gold = {key(a) for a in row["form"]}
        padded = {key(p["atom"]) for p in engine.predict_encoded([original, filler])[0]}
        perturbations = {
            "irrelevant_sentence": (row["text"] + " I left my umbrella near the door.", row["previous_text"]),
            "lowercase": (row["text"].lower(), row["previous_text"].lower()),
            "context_removed": (row["text"], ""),
        }
        changed = {"batch_padding": padded}
        for name, (text, prev) in perturbations.items():
            changed[name] = {key(p["atom"]) for p in engine.predict_encoded([encode(text, prev)])[0]}
        for name, prediction in changed.items():
            group = stats[row["domain"] + "/" + name]
            group.update(rows=1, unchanged=prediction == baseline,
                         original_exact=baseline == gold,
                         perturbed_exact=prediction == gold,
                         original_correct_became_wrong=baseline == gold and prediction != gold,
                         context_present=bool(row["previous_text"]))
            if name == "batch_padding" and prediction != baseline and len(examples) < 8:
                examples.append({"id": row["id"], "domain": row["domain"], "text": row["text"], "single": sorted(baseline), "padded": sorted(prediction)})
    for group in stats.values():
        group["invariance_rate"] = group["unchanged"] / group["rows"]
    report = {"seed": 9102026, "groups": dict(stats), "batch_padding_examples": examples,
              "seconds": time.monotonic() - start,
              "source_dev_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
              "model_sha256": hashlib.sha256((pathlib.Path(args.bundle) / "model.onnx").read_bytes()).hexdigest(),
              "scope": "Sampled development behavioral diagnostics. Context removal may genuinely change available information; measure sensitivity, not desired invariance. Lowercase may affect case-sensitive units; inspect individual cases."}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
