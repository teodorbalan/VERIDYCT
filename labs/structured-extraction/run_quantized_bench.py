"""Run six sequential constrained Docker benchmarks; retain failed receipts."""
import argparse
import collections
import hashlib
import json
import pathlib
import subprocess
import time


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True)
    p.add_argument("--image", default="veridyct-extractor:selected-v2")
    args = p.parse_args()
    root = pathlib.Path(args.root)
    q = root / "v3-audit/quantization"
    if (q / "benchmark-receipts.json").exists():
        raise ValueError("Receipts already exist; inspect rather than relaunch")
    image = json.loads(subprocess.check_output(["docker", "image", "inspect", args.image]))[0]
    cpulines = pathlib.Path("/proc/cpuinfo").read_text().splitlines()
    flags = next(x.split(":", 1)[1].split() for x in cpulines if x.startswith("flags"))
    receipt = {"image_id": image["Id"], "cpu_model": next(x.split(":", 1)[1].strip() for x in cpulines if x.startswith("model name")),
               "features": {name: name in flags for name in ["avx2", "avx512f", "avx512_vnni", "avx_vnni"]},
               "runs": []}
    for family in ["factorized", "v2ensemble"]:
        bundle = q / family
        exported = json.loads((bundle / "quantization-report.json").read_text())
        for variant, filename in [("fp32", "model.onnx"), ("dense_int8_rr", "dense_int8_rr.onnx"), ("recurrent_int8_rr", "recurrent_int8_rr.onnx")]:
            if variant != "fp32" and exported["variants"][variant]["status"] != "loadable":
                continue
            dest = q / "benchmarks" / (family + "-" + variant)
            dest.mkdir(parents=True)
            dest.chmod(0o777)
            command = ["docker", "run", "--name", f"veridyct-quant-{family}-{variant}", "--network", "none", "--read-only", "--cpus", "2", "--memory", "6g",
                       "--pids-limit", "128", "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--tmpfs", "/tmp:rw,nosuid,nodev,size=128m",
                       "--env", "PYTHONDONTWRITEBYTECODE=1", "--mount", f"type=bind,src={bundle},dst=/bundle,readonly",
                       "--mount", f"type=bind,src={q / 'benchmark_quantized_cpu.py'},dst=/benchmark.py,readonly",
                       "--mount", f"type=bind,src={root / 'data-v2/dev.jsonl'},dst=/data/dev.jsonl,readonly",
                       "--mount", f"type=bind,src={root / 'v3-audit/challenge-dev.jsonl'},dst=/data/challenge-dev.jsonl,readonly",
                       "--mount", f"type=bind,src={dest},dst=/output", "--entrypoint", "python", args.image,
                       "/benchmark.py", "--bundle", "/bundle", "--model", filename, "--data", "/data/dev.jsonl", "--fixture", "/data/challenge-dev.jsonl",
                       "--out", "/output/result", "--repeats", "3"]
            started = time.monotonic()
            with (dest / "docker.log").open("w") as f:
                result = subprocess.run(command, stdout=f, stderr=subprocess.STDOUT)
            record = {"family": family, "variant": variant, "command": command,
                      "exit_code": result.returncode, "wall_seconds": time.monotonic() - started,
                      "model_sha256": hashlib.sha256((bundle / filename).read_bytes()).hexdigest()}
            if (dest / "result/report.json").exists():
                record["report"] = json.loads((dest / "result/report.json").read_text())
            else:
                record["error"] = (dest / "docker.log").read_text()[-5000:]
            receipt["runs"].append(record)
            (q / "benchmark-receipts.json").write_text(json.dumps(receipt, indent=2) + "\n")
            print(f"{family} {variant} exit={result.returncode} wall={record['wall_seconds']:.2f}s", flush=True)
    comparisons = {}
    for family in ["factorized", "v2ensemble"]:
        basefile = q / "benchmarks" / (family + "-fp32") / "result/predictions.jsonl"
        if not basefile.exists():
            continue
        baseline = {r["id"]: r for r in map(json.loads, basefile.open())}
        for variant in ["dense_int8_rr", "recurrent_int8_rr"]:
            path = q / "benchmarks" / (family + "-" + variant) / "result/predictions.jsonl"
            if not path.exists():
                continue
            groups = collections.defaultdict(collections.Counter)
            for r in map(json.loads, path.open()):
                b = baseline[r["id"]]
                bs = {json.dumps(a, sort_keys=True) for a in b["prediction"]}
                rs = {json.dumps(a, sort_keys=True) for a in r["prediction"]}
                for group in [r["group"], "all"]:
                    groups[group].update(rows=1, prediction_changed=bs != rs,
                                         gained_correct=(not b["exact"]) and r["exact"],
                                         lost_correct=b["exact"] and (not r["exact"]))
            comparisons[family + "/" + variant] = dict(groups)
    (q / "prediction-changes.json").write_text(json.dumps(comparisons, indent=2) + "\n")
    print("COMPLETE", flush=True)


if __name__ == "__main__":
    main()
