"""Training-only robustness augmentation; never opens any new holdout archive.

Templates were authored with development-time assistant help. Their targets are
copied from training assertions, not background knowledge or truth judgments.
"""
import argparse
import collections
import copy
import hashlib
import json
import pathlib
import random
import re
import zipfile

import numpy as np
from grammar import Grammar, canonical
from prepare import norm, tokens, write_json
from prepare_mixed import render
from runtime import encode_input


DISTRACTORS = [
    "My lunch cost {n} euros.",
    "I waited {n} minutes for my own taxi.",
    "The local weather forecast gives a {n}% chance of rain.",
    "My personal notebook has {n} pages.",
    "I have {n} unread messages from my family.",
    "A neighbour counted {n} bicycles outside their house.",
    "My cousin's suitcase weighs {n} kg.",
    "My own train ticket cost {n} euros.",
    "The restaurant bill came to {n} dollars.",
    "My phone timer was set for {n} seconds.",
    "The fictional character in my novel has {n} dogs.",
    "My garden has {n} plants.",
]
PARAPHRASES = [
    "The entry for {s} gives {v} as the {a}.",
    "Concerning {s}: its {a} is listed as {v}.",
    "{v} is the recorded {a} of {s}.",
    "For {s}, the {a} field reads {v}.",
    "The figure quoted for {s}'s {a} is {v}.",
    "A note about {s} puts the {a} at {v}.",
    "{s} has a reported {a} of {v}.",
    "On the subject of {s}, {v} is given for its {a}.",
    "The {a} reported for {s} amounts to {v}.",
    "According to this statement, {s}'s {a} stands at {v}.",
]


def typed_text(value):
    op = value.get("op", "eq")
    prefix = {"eq": "", "lt": "less than ", "le": "at most ",
              "gt": "more than ", "ge": "at least "}[op]
    if value["kind"] == "date":
        prefix = {"eq": "", "lt": "before ", "le": "no later than ",
                  "gt": "after ", "ge": "no earlier than "}[op]
    if value["kind"] == "version":
        prefix = {"eq": "", "lt": "older than ", "le": "no newer than ",
                  "gt": "newer than ", "ge": "no older than "}[op]
    return prefix + render(value)


def transfer_labels(source, encoded, shift=0):
    """Only candidates at the original text's positions inherit labels."""
    labels = {(c["start"] + shift, c["end"] + shift, canonical(c["value"])):
              c.get("label", -100) for c in source["candidates"]}
    for c in encoded["candidates"]:
        c["label"] = labels.get((c["start"], c["end"], canonical(c["value"])), 0)


def atom_set(form):
    return {(a["subject"], a["attribute"], canonical(a["value"])) for a in form}


def covered(encoded, meta):
    return {(meta["pairs"][c["label"]-1][0], meta["pairs"][c["label"]-1][1],
             canonical(c["value"])) for c in encoded["candidates"] if c.get("label", 0)>0}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--glove", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    root, out = pathlib.Path(a.base), pathlib.Path(a.out)
    if out.exists():
        raise ValueError("Use a fresh immutable data directory")
    out.mkdir(parents=True)
    meta = json.loads((root/"meta.json").read_text())
    lex = json.loads((root/"lexicon.json").read_text())
    grammar = Grammar(lex, meta["extra_names"])
    train = [json.loads(x) for x in (root/"train.jsonl").open()]
    dev = [json.loads(x) for x in (root/"dev.jsonl").open()]
    dev_texts = {norm(r["text"]) for r in dev}
    pair_id = {tuple(pair): i+1 for i, pair in enumerate(meta["pairs"])}
    rng = random.Random(2026102903)
    # Keep original training multiplicity, but augment each unique parent text once.
    unique = list({(r["text"], r["previous_text"]): r for r in train
                   if ":repeat:" not in r["id"] and ":aug:" not in r["id"]}.values())
    rng.shuffle(unique)
    recipes = []
    for i, r in enumerate(unique):
        if i < 10000:
            noise = rng.choice(DISTRACTORS).format(n=rng.randint(2, 99))
            if i % 2:
                text = r["text"].rstrip() + " " + noise
                shift = 0
            else:
                text = noise + " " + r["text"]
                shift = len(noise)+1
            recipes.append((r, text, r["previous_text"], shift, "distractor", None))
        # Intervening context: retain the actual antecedent, add unrelated text.
        if r["previous_text"] and i < 6000:
            context = r["previous_text"] + " " + rng.choice(DISTRACTORS).format(n=rng.randint(2, 99))
            recipes.append((r, r["text"], context, 0, "context-gap", None))
        # This changes surface form, not the source subject/attribute/value.
        if len(r["form"]) == 1 and i < 10000:
            atom = r["form"][0]
            if atom["value"]["kind"] not in {"boolean", "name"}:
                text = PARAPHRASES[i % len(PARAPHRASES)].format(
                    s=atom["subject"], a=atom["attribute"].replace("_", " "),
                    v=typed_text(atom["value"]))
                recipes.append((r, text, "", 0, "paraphrase", atom))
    # Unrelated text and unsupported relations must map to no lexicon assertion.
    subjects = [s["name"] for s in lex["subjects"]]
    for i in range(1200):
        n = rng.randint(2, 99)
        text = rng.choice(DISTRACTORS).format(n=n)
        if i % 3 == 0:
            text = f"I wrote {rng.choice(subjects)} on a label. " + text
        elif i % 3 == 1:
            text = f"{rng.choice(subjects)} owns {n} purple submarines."
        source = dict(id=f"robust-negative-{i}", parent=f"robust-negative-{i}",
                      form=[], candidates=[], domain="robust")
        recipes.append((source, text, "", 0, "unrelated-negative", None))

    # Existing training vocabulary and vectors retain indices; additions use TRAIN only.
    old_size = len(meta["vocab"])
    for _, text, previous, _, _, _ in recipes:
        for word, _, _ in tokens(text+" "+previous):
            meta["vocab"].setdefault(word, len(meta["vocab"]))
            for ch in word:
                meta["chars"].setdefault(ch, len(meta["chars"]))
    vectors = np.random.default_rng(2026102903).normal(0, .15, (len(meta["vocab"]), 128)).astype(np.float32)
    vectors[:old_size] = np.load(root/"vectors.npy")
    additions = {w: i for w, i in meta["vocab"].items() if i >= old_size}
    hits = 0
    with zipfile.ZipFile(a.glove) as z:
        with z.open("glove.6B.100d.txt") as f:
            for line in f:
                word, _, tail = line.decode().partition(" ")
                if word in additions:
                    vec = np.fromstring(tail, sep=" ", dtype=np.float32)
                    if len(vec) == 100:
                        vectors[additions[word], :100] = vec
                        hits += 1
    np.save(out/"vectors.npy", vectors)
    meta["robust_augmentation"] = {
        "base_meta_sha256": hashlib.sha256((root/"meta.json").read_bytes()).hexdigest(),
        "seed": 2026102903, "provenance": "assistant-authored templates, deterministic training-only transformations; not truth labels",
        "new_vocab": len(meta["vocab"])-old_size, "new_glove_hits": hits,
        "new_final_test": "calibration-20000 and external-calibration gold remain unopened; independent challenge final withheld"}
    meta["vectors"]["npy_sha256"] = hashlib.sha256((out/"vectors.npy").read_bytes()).hexdigest()
    meta["vectors"]["base_vocab_total"] = meta["vectors"]["vocab_total"]
    meta["vectors"]["vocab_total"] = len(meta["vocab"])
    meta["vectors"]["vocab_hits"] += hits
    counts = collections.Counter()
    all_rows = []
    for r in train:
        encoded = encode_input(r["text"], r["previous_text"], meta, grammar, r["id"])
        transfer_labels(r, encoded)
        encoded.update({k:r[k] for k in ["form", "domain", "parent", "provenance"]})
        all_rows.append(encoded)
    seen = {(norm(r["text"]), norm(r["previous_text"])) for r in all_rows}
    for source, text, previous, shift, family, atom in recipes:
        if norm(text) in dev_texts:
            counts["rejected_dev_text_overlap"] += 1
            continue
        fingerprint = norm(text), norm(previous)
        if fingerprint in seen:
            counts["rejected_duplicate"] += 1
            continue
        try:
            encoded = encode_input(text, previous, meta, grammar, source["id"]+":robust:"+family)
        except ValueError:
            counts["rejected_length"] += 1
            continue
        if atom is not None:
            for c in encoded["candidates"]:
                c["label"] = pair_id[(atom["subject"], atom["attribute"])] if canonical(c["value"]) == canonical(atom["value"]) else 0
        else:
            transfer_labels(source, encoded, shift)
        if covered(encoded, meta) != atom_set(source["form"]):
            counts["rejected_incomplete_alignment"] += 1
            continue
        encoded.update(form=source["form"], domain=source["domain"], parent=source["parent"],
                       provenance="robust augmentation: "+family)
        all_rows.append(encoded)
        seen.add(fingerprint)
        counts[family] += 1
    with (out/"train.jsonl").open("w") as f:
        for r in all_rows:
            f.write(json.dumps(r, ensure_ascii=False)+"\n")
    with (out/"dev.jsonl").open("w") as f:
        for r in dev:
            encoded = encode_input(r["text"], r["previous_text"], meta, grammar, r["id"])
            transfer_labels(r, encoded)
            encoded.update({k:r[k] for k in ["form", "domain", "parent", "provenance"]})
            f.write(json.dumps(encoded, ensure_ascii=False)+"\n")
    train_parents = {r["parent"] for r in all_rows}
    assert not train_parents & {r["parent"] for r in dev}
    assert not {norm(r["text"]) for r in all_rows} & dev_texts
    counts.update(train_rows=len(all_rows), dev_rows=len(dev), base_rows=len(train),
                  normalized_text_overlap=0, parent_overlap=0)
    write_json(out/"meta.json", meta)
    write_json(out/"lexicon.json", lex)
    write_json(out/"preparation.json", dict(counts))
    print(json.dumps(dict(counts), indent=2), flush=True)


if __name__ == "__main__":
    main()
