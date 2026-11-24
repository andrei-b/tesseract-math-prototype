"""Measure z/2 reranking against hand-marked centers on single-line images."""
import argparse
from collections import Counter
import json
from pathlib import Path
from rerank import load_gray, suggestion, templates
from symbols import match_centers, read_symbols


def evaluate(manifest, inspector, bank):
    totals = Counter()
    decisions = []
    for entry in json.loads(manifest.read_text()):
        if "z2" not in entry:
            continue
        path = manifest.parent / entry["image"]
        gray = load_gray(path)
        symbols = read_symbols(inspector, path)
        gold = entry["z2"]
        matches = match_centers(gold, symbols)
        predictions = [suggestion(s, gray, bank) for s in symbols]
        for i, (x, label) in enumerate(gold):
            totals["printed_" + label] += 1
            j = matches.get(i)
            symbol = symbols[j] if j is not None else None
            before = symbol.text if symbol else None
            after = predictions[j] if symbol else None
            if symbol and bank.keys() <= symbol.choices.keys() and before in bank:
                totals["competing_choices"] += 1
            totals["stock_correct"] += before == label
            totals["reranked_correct"] += after == label
            totals["letters_recovered"] += label == "z" and before != "z" and after == "z"
            totals["true_digits_lost"] += label == "2" and before == "2" and after != "2"
            decisions.append(dict(image=entry["image"], x=x, gold=label, before=before, after=after,
                                  choices=symbol.choices if symbol else {}))
        labeled = set(matches.values())
        for j, s in enumerate(symbols):
            if j not in labeled and s.text != predictions[j]:
                totals["other_changes_to_review"] += 1
                decisions.append(dict(image=entry["image"], box=s.box, before=s.text,
                                      after=predictions[j], gold=None))
    return dict(totals=dict(totals), decisions=decisions)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("templates", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("inspector")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.manifest, args.inspector, templates(args.templates)), indent=2,
                     ensure_ascii=False))
