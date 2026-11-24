"""Compare native ink recovery with the placement-only patch, on identical images."""
import argparse
from collections import Counter
import json
from pathlib import Path
from symbols import match_centers, read_symbols


def score(symbols, gold):
    matches = match_centers(gold, symbols)
    hits = {j for j in matches.values() if symbols[j].sub}
    identities = {j for i, j in matches.items() if gold[i][1] == symbols[j].text}
    return Counter(symbols=len(symbols), matched=len(matches), named_indices=sum(c is not None for _, c in gold),
                   right_char=len(identities),
                   right_placement=len(hits), right_both=len(hits & identities),
                   false_flags=sum(s.sub for s in symbols) - len(hits),
                   other_symbols=len(symbols) - len(matches))


def compare(manifest, inspector):
    before, after = Counter(), Counter()
    rows = []
    for row in json.loads(manifest.read_text()):
        image = manifest.parent / row["image"]
        gold = row["subscripts"]
        old = read_symbols(inspector, image, enabled=True)
        new = read_symbols(inspector, image, enabled=True, recover=True)
        a, b = score(old, gold), score(new, gold)
        before.update(a)
        after.update(b)
        detail = dict(image=row["image"], printed=len(gold), changed=old != new, before=a, after=b)
        if old != new:
            detail.update(old_text="".join(s.text for s in old), new_text="".join(s.text for s in new))
            for stage, symbols in (("old_labels", old), ("new_labels", new)):
                match = match_centers(gold, symbols)
                detail[stage] = [dict(x=x, reference=c, ocr=symbols[match[i]].text if i in match else None,
                                      lowered=i in match and symbols[match[i]].sub)
                                 for i, (x, c) in enumerate(gold)]
        rows.append(detail)
    return dict(lines=rows, printed=sum(r["printed"] for r in rows), before=before, after=after)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("inspector")
    args = parser.parse_args()
    print(json.dumps(compare(args.manifest, args.inspector), indent=2, ensure_ascii=False))
