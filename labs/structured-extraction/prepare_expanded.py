"""Use all original rows from two authorized TRAIN worlds, with lineage control.

Never reads calibration/sealed/development archive gold. World IDs, expected
values, verdicts and selected evidence are never input features. A separate family
control is explicitly diagnostic, since earlier experiments saw these families.
"""
import argparse
import collections
import csv
import hashlib
import io
import json
import pathlib
import re
import zipfile

import numpy as np
from grammar import Grammar, canonical
from prepare import norm, tokens, ARCHIVE_SHA
from prepare_mixed import align
from runtime import encode_input

SOURCES = ["evaluation-data/realistic-synthetic-20000", "evaluation-data/realistic-v1/diagnostic-6000"]
SALT = "veridyct-family-holdout-v1:"


def read_base(path):
    rows = []
    for line in pathlib.Path(path).open():
        r = json.loads(line)
        row = {k: r[k] for k in ["id", "text", "previous_text", "form", "domain", "parent", "provenance"]}
        row["old_labels"] = {(c["start"], c["end"], canonical(c["value"])): c.get("label", -100) for c in r["candidates"]}
        rows.append(row)
    return rows


def root_id(row):
    return row.get("parent", row["id"]).split(":", 1)[0]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--archive", required=True)
    p.add_argument("--glove", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--min-family-rows", type=int, default=100)
    args = p.parse_args()
    base, output = pathlib.Path(args.base), pathlib.Path(args.out)
    if output.exists():
        raise ValueError("Use a fresh output root")
    output.mkdir(parents=True)
    archive = pathlib.Path(args.archive)
    if hashlib.sha256(archive.read_bytes()).hexdigest() != ARCHIVE_SHA:
        raise ValueError("Unexpected archive")
    original_meta = json.loads((base / "meta.json").read_text())
    lex = json.loads((base / "lexicon.json").read_text())
    originals, contexts = {}, {}
    source_hashes = {}
    with zipfile.ZipFile(archive) as z:
        for source in SOURCES:
            raw = z.read(source + "/gold/rows.jsonl")
            source_hashes[source] = hashlib.sha256(raw).hexdigest()
            # Select only training supervision/provenance fields immediately.
            gold = {}
            for line in raw.splitlines():
                item = json.loads(line)
                gold[item["id"]] = {k: item[k] for k in ["id", "text", "form", "assertion_spans", "template_family", "parent_scenario", "context_row_id"]}
            public = list(csv.DictReader(io.StringIO(z.read(source + "/public/universe.csv").decode())))
            for i, item in enumerate(public):
                row = gold[item["id"]]
                if item["text"] != row["text"]:
                    raise ValueError("Public/gold text mismatch")
                row["source_release"] = source
                originals[row["id"]] = row
                contexts[row["id"]] = [x["id"] for x in public[max(0, i - 3):i]]
    family_counts = collections.Counter(r["template_family"] for r in originals.values())
    eligible = [f for f, n in family_counts.items() if n >= args.min_family_rows]
    heldout = sorted(eligible, key=lambda f: hashlib.sha256((SALT + f).encode()).hexdigest())[:2]
    blocked_scenarios = {r["parent_scenario"] for r in originals.values() if r["template_family"] in heldout}
    blocked_ids = {r["id"] for r in originals.values() if r["parent_scenario"] in blocked_scenarios}
    protocol = {"allowed_sources": SOURCES, "source_gold_sha256": source_hashes,
                "source_original_rows": len(originals), "family_counts": dict(family_counts),
                "holdout_rule": f"Eligible families have >= {args.min_family_rows} original source rows; choose first two by SHA256({SALT!r} + family)",
                "heldout_families": heldout, "blocked_scenario_count": len(blocked_scenarios), "blocked_original_ids": len(blocked_ids),
                "context": "actual preceding three public CSV rows; excluded development/family rows omitted from that window, never gold context pointers",
                "family_metric_status": "development diagnostic, not a fresh blind test; earlier experiments used these families",
                "base_meta_sha256": hashlib.sha256((base / "meta.json").read_bytes()).hexdigest()}
    (output / "protocol.json").write_text(json.dumps(protocol, indent=2) + "\n")
    print(json.dumps(protocol, indent=2), flush=True)
    train_base, dev = read_base(base / "train.jsonl"), read_base(base / "dev.jsonl")
    dev_texts = {norm(r["text"]) for r in dev}
    dev_parents = {root_id(r) for r in dev}
    vector_base = np.load(base / "vectors.npy")
    all_prepared = {}
    for mode in ["expanded", "family_control"]:
        rejected = collections.Counter()
        blocked = blocked_ids if mode == "family_control" else set()
        train = []
        for row in train_base:
            parent = root_id(row)
            source = originals.get(parent)
            if parent in blocked:
                rejected["base_rows_from_heldout_scenario"] += 1
                continue
            # Exclusion metadata may use the known antecedent ID; no ID or gold
            # pointer enters model input. Derived context-gap examples retain
            # their original context only when that antecedent is not held out.
            if source and source["context_row_id"] in blocked and row["previous_text"]:
                rejected["base_rows_with_heldout_antecedent"] += 1
                continue
            if norm(row["text"]) in dev_texts or parent in dev_parents:
                rejected["base_rows_overlapping_dev"] += 1
                continue
            row = dict(row)
            if source:
                row.update(source_row_id=parent, source_release=source["source_release"],
                           template_family=source["template_family"], parent_scenario=source["parent_scenario"])
            train.append(row)
        existing = {norm(r["text"]) for r in train}
        new_originals = 0
        for parent, r in originals.items():
            if parent in blocked:
                rejected["originals_from_heldout_scenario"] += 1
                continue
            if norm(r["text"]) in dev_texts or parent in dev_parents:
                rejected["originals_overlapping_common_dev"] += 1
                continue
            if norm(r["text"]) in existing:
                rejected["originals_already_represented_or_duplicate"] += 1
                continue
            previous = " ".join(originals[x]["text"] for x in contexts[parent]
                                if x not in blocked and x not in dev_parents and norm(originals[x]["text"]) not in dev_texts)
            row = dict(id=parent + ":provided-full", parent=parent, text=r["text"], previous_text=previous,
                       form=r["form"], spans=r["assertion_spans"], domain="synthetic", source_row_id=parent,
                       source_release=r["source_release"], template_family=r["template_family"], parent_scenario=r["parent_scenario"],
                       provenance="original supplied training-world row; actual public previous-three context; no truth labels")
            train.append(row); existing.add(norm(r["text"])); new_originals += 1
        diagnostic = []
        if mode == "family_control":
            seen = set()
            forbidden = existing | dev_texts
            for parent in sorted(blocked):
                r = originals[parent]
                if norm(r["text"]) in forbidden or norm(r["text"]) in seen:
                    rejected["diagnostic_duplicate_or_train_dev_overlap"] += 1
                    continue
                seen.add(norm(r["text"]))
                previous = " ".join(originals[x]["text"] for x in contexts[parent])
                diagnostic.append(dict(id=parent + ":family-diagnostic", parent=parent, text=r["text"], previous_text=previous,
                                       form=r["form"], spans=r["assertion_spans"], domain="family_diagnostic",
                                       source_row_id=parent, source_release=r["source_release"],
                                       template_family=r["template_family"], parent_scenario=r["parent_scenario"],
                                       provenance="withheld training-world family diagnostic; earlier v2/v3 experiments may have used these families"))
        # Vocabularies must reflect the actual supported training samples.
        def supported(row):
            return len(tokens(row["text"])) + min(96, len(tokens(row["previous_text"]))) + 2 <= original_meta["max_tokens"]
        supported_train = [r for r in train if supported(r)]
        rejected["overlength_train_rows"] = len(train) - len(supported_train)
        train = supported_train
        new_originals = sum(r["id"].endswith(":provided-full") for r in train)
        assert not {norm(r['text']) for r in train} & dev_texts
        assert not {root_id(r) for r in train} & dev_parents
        if mode == "family_control":
            assert not {r.get("source_row_id") for r in train} & blocked
            assert not {r.get("parent_scenario") for r in train} & blocked_scenarios
        extras = sorted({a["value"]["value"] for r in train for a in r["form"] if a["value"]["kind"] == "name"})
        vocab = {"<pad>": 0, "<unk>": 1, "<ctx>": 2, "<current>": 3}
        for row in train:
            for w, _, _ in tokens(row["text"] + " " + row["previous_text"]):
                vocab.setdefault(w, len(vocab))
        chars = {"<pad>": 0, "<unk>": 1}
        for word in vocab:
            for char in word:
                chars.setdefault(char, len(chars))
        meta = {k: v for k, v in original_meta.items() if k not in ["vocab", "chars", "vectors", "extra_names"]}
        meta.update(vocab=vocab, chars=chars, extra_names=extras,
                    expanded_training=dict(protocol, mode=mode, new_original_provided_rows=new_originals,
                                           base_rows_retained=len(train) - new_originals, train_rows=len(train),
                                           family_diagnostic_rows=len(diagnostic), exclusions=dict(rejected)))
        all_prepared[mode] = (train, dev, diagnostic, meta)
        print(mode, json.dumps(meta["expanded_training"]), flush=True)
    # Read only GloVe vectors requested by actual training vocabularies.
    wanted = set().union(*(set(t[3]["vocab"]) for t in all_prepared.values()))
    pretrained = {}
    with zipfile.ZipFile(args.glove) as z:
        with z.open("glove.6B.100d.txt") as f:
            for line in f:
                word, _, tail = line.decode().partition(" ")
                if word in wanted:
                    v = np.fromstring(tail, sep=" ", dtype=np.float32)
                    if len(v) == 100:
                        pretrained[word] = v
    for mode, (train, dev, diagnostic, meta) in all_prepared.items():
        dest = output / mode
        dest.mkdir()
        vectors = np.zeros((len(meta["vocab"]), 128), dtype=np.float32)
        for word, index in meta["vocab"].items():
            if word in original_meta["vocab"]:
                vectors[index] = vector_base[original_meta["vocab"][word]]
            else:
                seed = int(hashlib.sha256(("expanded-vectors:" + word).encode()).hexdigest()[:16], 16)
                vectors[index] = np.random.default_rng(seed).normal(0, .15, 128)
            if word in pretrained:
                vectors[index, :100] = pretrained[word]
        vectors[0] = 0
        np.save(dest / "vectors.npy", vectors)
        meta["vectors"] = dict(original_meta["vectors"], vocab_total=len(meta["vocab"]),
                               vocab_hits=sum(w in pretrained for w in meta["vocab"]),
                               npy_sha256=hashlib.sha256((dest / "vectors.npy").read_bytes()).hexdigest(),
                               policy="train-only vocabulary; common base static/random vectors retained, new tails word-hash seeded; no trained embeddings imported")
        grammar = Grammar(lex, meta["extra_names"])
        pair_id = {(s, a): i + 1 for i, (s, a) in enumerate(meta["pairs"])}
        counts = {}
        for split, rows in [("train", train), ("dev", dev), ("family-diagnostic", diagnostic)]:
            counter = collections.Counter()
            with (dest / (split + ".jsonl")).open("w") as f:
                for row in rows:
                    try:
                        encoded = encode_input(row["text"], row["previous_text"], meta, grammar, row["id"])
                    except ValueError as exc:
                        if "384" not in str(exc):
                            raise
                        if split == "dev":
                            raise ValueError("Frozen common development cannot change") from exc
                        counter["overlength_rows_excluded"] += 1
                        continue
                    if "old_labels" in row:
                        for c in encoded["candidates"]:
                            c["label"] = row["old_labels"].get((c["start"], c["end"], canonical(c["value"])), 0)
                    else:
                        align(row, encoded, pair_id, lex)
                    encoded.update({k: row[k] for k in ["form", "domain", "parent", "provenance", "source_row_id", "source_release", "template_family", "parent_scenario"] if k in row})
                    counter.update(rows=1, atoms=len(row["form"]), candidates=len(encoded["candidates"]),
                                   ignored_candidates=sum(c["label"] == -100 for c in encoded["candidates"]))
                    counter[row["domain"] + "_rows"] += 1
                    proposed = {canonical(c["value"]) for c in encoded["candidates"]}
                    counter["value_candidate_missing_atoms"] += sum(canonical(a["value"]) not in proposed for a in row["form"])
                    f.write(json.dumps(encoded, ensure_ascii=False) + "\n")
            counts[split] = dict(counter)
        (dest / "meta.json").write_text(json.dumps(meta, ensure_ascii=False))
        (dest / "lexicon.json").write_text(json.dumps(lex, ensure_ascii=False))
        (dest / "preparation.json").write_text(json.dumps(counts, indent=2))
        print("PREPARED", mode, json.dumps(counts), flush=True)


if __name__ == "__main__":
    main()
