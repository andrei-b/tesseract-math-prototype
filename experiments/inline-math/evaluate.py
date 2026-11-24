"""Measure script placement on photographed or generated single-line images."""
import argparse
from collections import Counter
import json
from pathlib import Path
from symbols import match_centers, read_symbols


def evaluate(manifest, inspector, baseline=None):
    counts = Counter()
    details = []
    for entry in json.loads(manifest.read_text()):
        image = manifest.parent / entry["image"]
        off = read_symbols(inspector, image)
        if baseline and off != read_symbols(baseline, image):
            raise ValueError(f"Stock and patched default outputs differ on {image}")
        on = read_symbols(inspector, image, enabled=True)
        if len(off) != len(on) or any((a.text, a.box, a.word, a.sup, a.choices) !=
                                      (b.text, b.box, b.word, b.sup, b.choices)
                                      for a, b in zip(off, on)):
            raise ValueError(f"Enabling subscript placement changed OCR on {image}")
        gold = entry["subscripts"]
        match = match_centers(gold, on)
        locations = set(match.values())
        flags = {j for j, s in enumerate(on) if s.sub}
        stock_flags = {j for j, s in enumerate(off) if s.sub}
        line = dict(positives=len(gold), matched_boxes=len(locations),
                    baseline_tp=len(locations & stock_flags), baseline_fp=len(stock_flags - locations),
                    tp=len(flags & locations), fp=len(flags - locations),
                    correct_identity=sum(on[j].text == gold[i][1] for i, j in match.items() if j in flags),
                    other_ocr_symbols=len(on) - len(locations))
        counts.update(line)
        details.append(dict(image=entry["image"], counts=line,
                            false_flags=[dict(text=on[j].text, box=on[j].box, word=on[j].word)
                                         for j in sorted(flags - locations)],
                            labeled=[dict(x=x, gold=c, symbol=on[match[i]].text if i in match else None,
                                          flagged=match.get(i) in flags) for i, (x, c) in enumerate(gold)]))
    return dict(lines=details, totals=dict(counts))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("inspector")
    parser.add_argument("--stock", help="The same inspector linked to stock Tesseract")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.manifest, args.inspector, args.stock), indent=2, ensure_ascii=False))
