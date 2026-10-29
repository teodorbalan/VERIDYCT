"""Fixed development inputs, independent CPU process per FP32/INT8 variant."""
import argparse
import collections
import hashlib
import json
import pathlib
import resource
import statistics
import sys
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", required=True)
    p.add_argument("--model", default="model.onnx")
    p.add_argument("--data", required=True)
    p.add_argument("--fixture", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--batch", type=int, default=48)
    args = p.parse_args()
    fixture = pathlib.Path(args.fixture)
    if "final" in fixture.name:
        raise ValueError("Only development fixtures may be benchmarked")
    out = pathlib.Path(args.out)
    if out.exists():
        raise ValueError("Use a fresh benchmark directory")
    out.mkdir(parents=True)
    total_start = time.monotonic()
    sys.path.insert(0, args.bundle)
    from runtime import CpuExtractor, encode_input
    from grammar import canonical
    session_start = time.monotonic()
    engine = CpuExtractor(args.bundle, model=args.model, threads=2)
    session_seconds = time.monotonic() - session_start
    raw = [json.loads(x) for x in pathlib.Path(args.data).open()]
    for r in raw:
        r["metric_group"] = r["domain"]
    challenge = [json.loads(x) for x in fixture.open()]
    if any(r.get("split") != "dev" for r in challenge):
        raise ValueError("Reserved split rejected")
    for r in challenge:
        r["metric_group"] = "challenge_diagnostic" if r.get("ambiguous") or r.get("diagnostic") else "challenge_primary"
    raw += challenge
    prep_start = time.monotonic()
    rows = [dict(encode_input(r["text"], r.get("previous_text", ""), engine.meta, engine.grammar, r["id"]), gold=r["form"], metric_group=r["metric_group"]) for r in raw]
    rows.sort(key=lambda r: len(r["tokens"]))
    preparation_seconds = time.monotonic() - prep_start
    key = lambda a: (a["subject"], a["attribute"], canonical(a["value"]))
    stats = collections.defaultdict(collections.Counter)
    pred_records, baseline_sets, times = [], [], []
    engine.predict_encoded(rows[:args.batch])
    for repeat in range(args.repeats):
        started = time.monotonic()
        sets = []
        for i in range(0, len(rows), args.batch):
            chosen = rows[i:i + args.batch]
            for row, prediction in zip(chosen, engine.predict_encoded(chosen)):
                actual = {key(a["atom"]) for a in prediction}
                sets.append(actual)
                if repeat == 0:
                    expected = {key(a) for a in row["gold"]}
                    for group in [row["metric_group"], "all"]:
                        stats[group].update(rows=1, exact=actual == expected, gold=len(expected), predicted=len(actual), correct=len(actual & expected))
                    pred_records.append({"id": row["id"], "group": row["metric_group"], "prediction": [a["atom"] for a in prediction], "exact": actual == expected})
        times.append(time.monotonic() - started)
        if repeat == 0:
            baseline_sets = sets
        elif sets != baseline_sets:
            raise AssertionError("Repeated CPU evaluation changed decoded predictions")
    for group in stats.values():
        group["exact_rate"] = group["exact"] / group["rows"]
        group["f1"] = 2 * group["correct"] / max(1, group["gold"] + group["predicted"])
    model_path = pathlib.Path(args.bundle) / args.model
    report = {"model": args.model, "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
              "model_bytes": model_path.stat().st_size, "cpu_threads": 2, "batch": args.batch,
              "groups": dict(stats), "session_load_seconds": session_seconds,
              "preparation_seconds": preparation_seconds, "inference_seconds": times,
              "median_inference_seconds": statistics.median(times),
              "median_rows_per_second": len(rows) / statistics.median(times),
              "total_seconds_including_repeats": time.monotonic() - total_start,
              "peak_process_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              "source_dev_sha256": hashlib.sha256(pathlib.Path(args.data).read_bytes()).hexdigest(),
              "challenge_dev_sha256": hashlib.sha256(fixture.read_bytes()).hexdigest(),
              "scope": "Repeated inference timings on prepared development inputs; preprocessing/session costs separately reported. No final gold or calibration."}
    (out / "predictions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in pred_records))
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
