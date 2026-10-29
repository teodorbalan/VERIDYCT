"""Isolated ORT dynamic-INT8 exports; no calibration data or model training."""
import argparse
import collections
import hashlib
import json
import pathlib
import platform
import shutil
import time
import traceback

import onnx
import onnxruntime as ort
from onnxruntime.quantization import QuantType, quantize_dynamic


def describe(path):
    model = onnx.load(path)
    return {"bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "operators": dict(collections.Counter(n.op_type for n in model.graph.node)),
            "initializer_dtypes": dict(collections.Counter(onnx.TensorProto.DataType.Name(t.data_type) for t in model.graph.initializer))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bundle", required=True)
    p.add_argument("--out", required=True)
    args = p.parse_args()
    source, out = pathlib.Path(args.bundle), pathlib.Path(args.out)
    if out.exists():
        raise ValueError("Use a fresh export directory")
    out.mkdir(parents=True)
    source_hash = hashlib.sha256((source / "model.onnx").read_bytes()).hexdigest()
    for name in ["model.onnx", "meta.json", "lexicon.json", "grammar.py", "prepare.py", "runtime.py"]:
        shutil.copyfile(source / name, out / name)
    report = {"source_bundle": str(source), "onnxruntime": ort.__version__, "onnx": onnx.__version__,
              "platform": platform.platform(), "fp32": describe(out / "model.onnx"),
              "mode": "dynamic activation quantization with signed INT8 stored weights; reduce_range=True uses effective 7-bit weight range; NOT pure weight-only W8A32",
              "settings": {"weight_type": "QInt8", "per_channel": False, "reduce_range": True, "MatMulConstBOnly": True},
              "variants": {}}
    for name, ops in [("dense_int8_rr", ["MatMul", "Gemm"]),
                      ("recurrent_int8_rr", ["MatMul", "Gemm", "LSTM"])]:
        path = out / (name + ".onnx")
        started = time.monotonic()
        try:
            quantize_dynamic(str(source / "model.onnx"), str(path), op_types_to_quantize=ops,
                             weight_type=QuantType.QInt8, per_channel=False, reduce_range=True,
                             extra_options={"MatMulConstBOnly": True})
            onnx.checker.check_model(str(path))
            options = ort.SessionOptions()
            options.intra_op_num_threads = 2
            options.inter_op_num_threads = 1
            ort.InferenceSession(str(path), options, providers=["CPUExecutionProvider"])
            report["variants"][name] = dict(describe(path), operators_requested=ops, status="loadable", seconds=time.monotonic() - started)
        except Exception:
            report["variants"][name] = {"status": "failed", "operators_requested": ops,
                                         "seconds": time.monotonic() - started, "error": traceback.format_exc()}
        (out / "quantization-report.json").write_text(json.dumps(report, indent=2) + "\n")
    assert hashlib.sha256((source / "model.onnx").read_bytes()).hexdigest() == source_hash
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
