"""Training-only lexical baseline and train/development difficulty audit.

Does not read archive calibration or sealed releases. The retrieval baseline
predicts subject/attribute SETS only, so its numbers are not full JSON accuracy.
"""
import argparse
import collections
import hashlib
import json
import math
import pathlib
import re
import time

import numpy as np


def load(path):
    return [json.loads(line) for line in pathlib.Path(path).open(encoding="utf-8")]


def norm(text):
    return " ".join(text.casefold().split())


def pairs(row):
    return {(a["subject"], a["attribute"]) for a in row["form"]}


def words(text):
    tokens = re.findall(r"\w+", re.sub(r"\d+(?:[.,]\d+)*", " NUMBER ", text.casefold()))
    return collections.Counter(tokens + ["~".join(x) for x in zip(tokens, tokens[1:])])


class LexicalNearest:
    """Exact cosine retrieval over word unigram/bigram TF-IDF, train vocabulary."""

    def __init__(self, rows):
        # Deduplicate repeats/augmentations sharing normalized numeric text.
        unique = {}
        for row in rows:
            signature = re.sub(r"\d+(?:[.,]\d+)*", " NUMBER ", norm(row["text"]))
            unique.setdefault(signature, row)
        self.rows = list(unique.values())
        features = [words(row["text"]) for row in self.rows]
        df = collections.Counter(t for row in features for t in row)
        self.idf = {t: math.log((1 + len(features)) / (1 + n)) + 1 for t, n in df.items()}
        indices = collections.defaultdict(list)
        weights = collections.defaultdict(list)
        for i, row in enumerate(features):
            weighted = {t: (1 + math.log(n)) * self.idf[t] for t, n in row.items()}
            length = math.sqrt(sum(v * v for v in weighted.values())) or 1
            for t, v in weighted.items():
                indices[t].append(i)
                weights[t].append(v / length)
        self.postings = {t: (np.asarray(v, dtype=np.int32), np.asarray(weights[t], dtype=np.float32)) for t, v in indices.items()}

    def predict(self, text):
        query = {t: (1 + math.log(n)) * self.idf[t] for t, n in words(text).items() if t in self.idf}
        length = math.sqrt(sum(v * v for v in query.values())) or 1
        scores = np.zeros(len(self.rows), dtype=np.float32)
        for t, v in query.items():
            ix, weights = self.postings[t]
            scores[ix] += weights * (v / length)
        i = int(scores.argmax())
        return pairs(self.rows[i]), float(scores[i])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = pathlib.Path(args.data)
    out = pathlib.Path(args.out)
    if out.exists():
        raise ValueError("Use a fresh output file")
    train, dev = load(root / "train.jsonl"), load(root / "dev.jsonl")
    lex = json.loads((root / "lexicon.json").read_text())
    names = sorted({norm(n) for s in lex["subjects"] for n in [s["name"], *s["aliases"]]}, key=len, reverse=True)
    name_re = re.compile(r"(?<!\w)(?:" + "|".join(map(re.escape, names)) + r")(?!\w)")

    def skeleton(text, entities=False):
        s = norm(text)
        if entities:
            s = name_re.sub("ENTITY", s)
        return " ".join(re.sub(r"\d+(?:[.,]\d+)*", " NUMBER ", s).split())

    raw = {norm(r["text"]) for r in train}
    number_templates = {skeleton(r["text"]) for r in train}
    full_templates = {skeleton(r["text"], True) for r in train}
    started = time.monotonic()
    retriever = LexicalNearest(train)
    stats = collections.defaultdict(collections.Counter)
    for row in dev:
        group = stats[row["domain"]]
        expected = pairs(row)
        predicted, similarity = retriever.predict(row["text"])
        group.update(rows=1, exact_text_overlap=norm(row["text"]) in raw,
                     number_template_overlap=skeleton(row["text"]) in number_templates,
                     entity_number_template_overlap=skeleton(row["text"], True) in full_templates,
                     pair_set_exact=predicted == expected, correct_pairs=len(predicted & expected),
                     gold_pairs=len(expected), predicted_pairs=len(predicted),
                     explicit_context_rows=bool(row["previous_text"]),
                     multiple_atom_rows=len(row["form"]) > 1,
                     whitespace_tokens=len(row["text"].split()),
                     cosine_sum=similarity)
    for group in stats.values():
        group["pair_set_exact_rate"] = group["pair_set_exact"] / group["rows"]
        group["pair_f1"] = 2 * group["correct_pairs"] / (group["gold_pairs"] + group["predicted_pairs"])
        group["mean_words"] = group["whitespace_tokens"] / group["rows"]
        group["mean_nearest_cosine"] = group["cosine_sum"] / group["rows"]
    report = {"scope": "TF-IDF nearest training sentence predicts only subject/attribute sets, not values or full JSON", "rows_train": len(train), "retrieval_unique_number_templates": len(retriever.rows), "stats": dict(stats), "seconds": time.monotonic() - started,
              "source_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [root / "train.jsonl", root / "dev.jsonl", root / "meta.json"]},
              "template_definition": "case/whitespace normalized; digits replaced, optionally longest public entity names replaced; punctuation and ordinary words retained", "code_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
