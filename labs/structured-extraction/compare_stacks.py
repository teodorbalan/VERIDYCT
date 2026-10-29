"""Common development comparison across model families and vocabulary versions.

No final/calibration archive is accepted. Checkpoint epochs were selected by the
original official/synthetic mean; final stack choice adds a behavioral DEV suite.
"""
import argparse
import hashlib
import json
import pathlib
import time
import numpy as np
import torch
from torch import nn
from grammar import Grammar, canonical
from model import Extractor, collate
from runtime import encode_input
from train import read_rows, key


def load_any(checkpoint):
    ck = torch.load(checkpoint, map_location="cpu", weights_only=False)
    meta = ck["meta"]
    if "schema" in ck:
        from model_factorized import FactorizedExtractor
        model = FactorizedExtractor(len(meta["vocab"]), len(meta["chars"]),
                                    len(meta["pairs"]), ck["config"], ck["schema"])
    elif "label_graph_layers" in ck["config"]:
        from model_graph import GraphExtractor
        model = GraphExtractor(meta, ck["config"])
    else:
        model = Extractor(len(meta["vocab"]), len(meta["chars"]), len(meta["pairs"]), ck["config"])
    model.load_state_dict(ck["model"])
    model.eval()
    if "label_graph_layers" in ck["config"] and not ck["config"].get("candidate_graph_layers", 0):
        from model_graph import fold_graph_head
        model = fold_graph_head(model, meta)
    return model, ck


class MappedExtractor(nn.Module):
    def __init__(self, model, master, member):
        super().__init__()
        if master["pairs"] != member["pairs"]:
            raise ValueError("Output label orders differ")
        self.model = model
        for field in ["vocab", "chars"]:
            table = [1]*len(master[field])
            for token, i in master[field].items():
                table[i] = member[field].get(token, 1)
            self.register_buffer(field+"_map", torch.tensor(table))

    def forward(self, words, chars, spans, clauses, kinds):
        return self.model(self.vocab_map[words], self.chars_map[chars], spans, clauses, kinds)


class MixedEnsemble(nn.Module):
    def __init__(self, models):
        super().__init__()
        self.models = nn.ModuleList(models)

    def forward(self, words, chars, spans, clauses, kinds):
        probs = [m(words, chars, spans, clauses, kinds).softmax(-1) for m in self.models]
        return torch.stack(probs).mean(0).clamp_min(1e-12).log()


def decode_probability(row, prob, pairs):
    result, seen = [], set()
    labels = prob.argmax(-1)
    for j, candidate in enumerate(row["candidates"]):
        label = int(labels[j])
        score = float(prob[j, label])
        if label == 0 or score < .5:
            continue
        subject, attribute = pairs[label-1]
        atom = dict(subject=subject, attribute=attribute, value=candidate["value"])
        k = key(atom)
        if k in seen:
            continue
        seen.add(k)
        result.append(dict(atom=atom, model_score=score,
                           value_span_chars=[candidate["start"], candidate["end"]]))
    return result


def evaluate_probabilities(rows, offsets, probabilities, pairs, path=None):
    stats = {}
    stream = open(path, "w") if path else None
    for i, row in enumerate(rows):
        prediction = decode_probability(row, probabilities[offsets[i]:offsets[i+1]], pairs)
        gold, actual = {key(x) for x in row["form"]}, {key(x["atom"]) for x in prediction}
        domain = row["domain"]
        d = stats.setdefault(domain, dict(rows=0, exact=0, gold=0, predicted=0, correct=0))
        d["rows"] += 1
        d["exact"] += gold == actual
        d["gold"] += len(gold)
        d["predicted"] += len(actual)
        d["correct"] += len(gold & actual)
        if stream:
            stream.write(json.dumps(dict(id=row["id"], domain=domain, text=row["text"],
                                         previous_text=row["previous_text"], gold=row["form"],
                                         prediction=prediction, exact=gold == actual))+"\n")
    if stream:
        stream.close()
    for d in stats.values():
        d["exact_rate"] = d["exact"]/max(1, d["rows"])
        d["f1"] = 2*d["correct"]/max(1, d["gold"]+d["predicted"])
        d["precision"] = d["correct"]/max(1, d["predicted"])
        d["recall"] = d["correct"]/max(1, d["gold"])
    score = .5*stats["official"]["exact_rate"]+.25*stats["synthetic"]["exact_rate"]+.25*stats["challenge"]["exact_rate"]
    return dict(domains=stats, selection_score=score)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--registry", required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--challenge-dev", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--cache", required=True)
    p.add_argument("--grammar", choices=["baseline", "robust"], default="robust")
    a = p.parse_args()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    root, out, cache = pathlib.Path(a.data), pathlib.Path(a.out), pathlib.Path(a.cache)
    if out.exists():
        raise ValueError("Use a fresh comparison directory")
    out.mkdir(parents=True)
    cache.mkdir(parents=True, exist_ok=True)
    meta = json.loads((root/"meta.json").read_text())
    registry = json.loads(pathlib.Path(a.registry).read_text())
    # A union of TRAIN-built member vocabularies avoids losing words known only
    # to a newer member. Each network still receives its own indices or UNK.
    for record in registry["singles"]:
        ck = torch.load(record["checkpoint"], map_location="cpu", weights_only=False)
        if ck["meta"]["pairs"] != meta["pairs"]:
            raise ValueError("Member output labels differ")
        for field in ["vocab", "chars"]:
            for token in ck["meta"][field]:
                meta[field].setdefault(token, len(meta[field]))
        del ck
    (out/"meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    lex = json.loads((root/"lexicon.json").read_text())
    raw = read_rows(root/"dev.jsonl")
    challenge = read_rows(a.challenge_dev)
    if any(x.get("split") != "dev" for x in challenge):
        raise ValueError("Only declared development fixtures are accepted")
    raw += [dict(x, domain="challenge") for x in challenge if not x.get("ambiguous") and not x.get("diagnostic")]
    base_grammar = Grammar(lex, meta["extra_names"])
    selected_grammar = base_grammar
    if a.grammar == "robust":
        from grammar_robust import RobustGrammar
        selected_grammar = RobustGrammar(lex, meta["extra_names"])
    rows = []
    for r in raw:
        row = encode_input(r["text"], r.get("previous_text", ""), meta, selected_grammar, r["id"])
        original = encode_input(r["text"], r.get("previous_text", ""), meta, base_grammar, r["id"])
        # Values are metadata used by decoding, never neural input features.
        for field in ["tokens", "chars", "current_offset", "has_context"]:
            assert row[field] == original[field]
        assert [{k:v for k,v in c.items() if k != "value"} for c in row["candidates"]] == [
            {k:v for k,v in c.items() if k != "value"} for c in original["candidates"]]
        row.update(form=r["form"], domain=r["domain"])
        rows.append(row)
    rows.sort(key=lambda r:(len(r["tokens"]), r["id"]))
    offsets = np.cumsum([0]+[len(r["candidates"]) for r in rows])
    fingerprint = [dict(id=r["id"], tokens=r["tokens"], chars=r["chars"],
                        candidates=[{k:v for k,v in c.items() if k != "value"} for c in r["candidates"]])
                   for r in rows]
    implementation_hashes = {name:hashlib.sha256((pathlib.Path(__file__).parent/name).read_bytes()).hexdigest()
                             for name in ['compare_stacks.py','model.py','model_factorized.py','model_graph.py','runtime.py','grammar.py','grammar_robust.py','prepare.py']}
    cache_identity = dict(inputs=fingerprint, implementation=implementation_hashes,
                          master_meta_sha256=hashlib.sha256((out/'meta.json').read_bytes()).hexdigest(),
                          batch_policy='length,id sorted; batches48; vocabulary mapped per checkpoint')
    input_digest = hashlib.sha256(json.dumps(cache_identity, sort_keys=True).encode()).hexdigest()
    models, options, probabilities = {}, [], {}
    for record in registry["singles"]:
        name = record["name"]
        sha = hashlib.sha256(pathlib.Path(record["checkpoint"]).read_bytes()).hexdigest()
        target = cache/(sha+"-"+input_digest+".npy")
        start = time.monotonic()
        model, ck = load_any(record["checkpoint"])
        mapped = MappedExtractor(model, meta, ck["meta"]).eval()
        count = sum(x.numel() for x in model.parameters())
        if not target.exists():
            array = np.lib.format.open_memmap(target.with_suffix(".tmp.npy"), mode="w+", dtype=np.float32,
                                              shape=(int(offsets[-1]), len(meta["pairs"])+1))
            with torch.inference_mode():
                for start_row in range(0, len(rows), 48):
                    selected = rows[start_row:start_row+48]
                    prob = mapped(*collate(selected)[0]).softmax(-1).numpy()
                    for j, r in enumerate(selected):
                        index = start_row+j
                        array[offsets[index]:offsets[index+1]] = prob[j, :len(r["candidates"])]
            array.flush()
            del array
            target.with_suffix(".tmp.npy").replace(target)
        probabilities[name] = np.load(target, mmap_mode="r")
        result = evaluate_probabilities(rows, offsets, probabilities[name], meta["pairs"], out/(name+".jsonl"))
        result.update(name=name, members=[name], parameters=count, seconds=time.monotonic()-start)
        record.update(sha256=sha, parameters=count)
        models[name] = record
        options.append(result)
        print(json.dumps(result), flush=True)
        del model, mapped, ck
    ranked = sorted(options, key=lambda x:(x["selection_score"], -x["parameters"]), reverse=True)
    combinations = [(f"top-{n}", [x["name"] for x in ranked[:n]]) for n in [2,3,4] if len(ranked)>=n]
    if registry.get("previous_ensemble"):
        combinations.append(("previous-v2-ensemble", registry["previous_ensemble"]))
    for name, members in combinations:
        mean = sum(np.asarray(probabilities[m]) for m in members)/len(members)
        result = evaluate_probabilities(rows, offsets, mean, meta["pairs"], out/(name+".jsonl"))
        result.update(name=name, members=members, parameters=sum(models[m]["parameters"] for m in members))
        options.append(result)
        print(json.dumps(result), flush=True)
    selected = max(options, key=lambda x:(x["selection_score"], -x["parameters"]))
    manifest = dict(policy="official50%,synthetic25%,challenge-dev25%; all singles plus uniform top2/3/4 and prior-v2 control; ties fewer parameters",
                    selected=selected, options=options, models=models,
                    members=[models[m] for m in selected["members"]], grammar=a.grammar,
                    master_meta_sha256=hashlib.sha256((out/"meta.json").read_bytes()).hexdigest(),
                    input_digest=input_digest, final_gold_read=False,
                    inference_implementation_sha256=implementation_hashes,
                    challenge_dev_sha256=hashlib.sha256(pathlib.Path(a.challenge_dev).read_bytes()).hexdigest())
    (out/"selection.json").write_text(json.dumps(manifest, indent=2))
    print("SELECTED "+json.dumps(selected), flush=True)


if __name__ == "__main__":
    main()
