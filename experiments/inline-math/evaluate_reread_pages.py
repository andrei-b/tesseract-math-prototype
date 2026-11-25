"""Compare the selective pass on six full pages with a separately annotated subset."""
import argparse
from collections import Counter
import io
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image

from symbols import read_symbols


def render(source, number, target):
    if source.suffix.lower() == ".djvu":
        pixels = subprocess.check_output(["ddjvu", "-format=pgm", "-scale=300",
                                          f"-page={number}", str(source), "-"])
        with Image.open(io.BytesIO(pixels)) as image:
            image.save(target)
    else:
        subprocess.run(["pdftoppm", "-gray", "-r", "220", "-f", str(number), "-l", str(number),
                        "-singlefile", "-png", str(source), str(target.with_suffix(""))], check=True)


def labeled_scores(labels, symbols):
    pairs = []
    for i, (x, y, _) in enumerate(labels):
        for j, symbol in enumerate(symbols):
            l, t, r, b = symbol.box
            dx = abs(x - (l + r) / 2)
            dy = abs(y - (t + b) / 2)
            if l - 2 <= x <= r + 2 and t - 2 <= y <= b + 2 and dx <= max(3, (b - t) * .45):
                pairs.append((dx * dx + dy * dy, i, j))
    matched, used = set(), set()
    scores = Counter(printed=len(labels), matched=0, identity=0, placed=0, both=0)
    for _, i, j in sorted(pairs):
        if i in matched or j in used:
            continue
        matched.add(i)
        used.add(j)
        right = labels[i][2] == symbols[j].text
        scores.update(matched=1, identity=int(right), placed=int(symbols[j].sub),
                      both=int(right and symbols[j].sub))
    return scores


def evaluate(sources, inspector, directory):
    specs = json.loads(Path(__file__).with_name("reread-pages.json").read_text())
    rows = []
    totals = {"before": Counter(), "after": Counter()}
    for page in specs:
        path = directory / page["image"]
        render(sources / page["source"], page["file_page"], path)
        with Image.open(path) as image:
            if list(image.size) != page["size"]:
                raise ValueError(f"Annotations for {path.name} require image size {page['size']}")
        before = read_symbols(inspector, path, enabled=True, recover=True, layout="auto")
        after = read_symbols(inspector, path, enabled=True, recover=True, layout="auto", reread=True)
        if [s.box for s in before] != [s.box for s in after]:
            raise ValueError(f"Symbol boxes changed on {path.name}. Review alignment before scoring.")
        changes = [dict(box=o.box, before=o.text, after=n.text, word_before=o.word,
                        word_after=n.word, sub_before=o.sub, sub_after=n.sub)
                   for o, n in zip(before, after) if (o.text, o.sub) != (n.text, n.sub)]
        row = dict(image=path.name, symbols=len(before), changes=changes)
        for name, symbols in [("before", before), ("after", after)]:
            row[name] = labeled_scores(page["subscripts"], symbols)
            totals[name].update(row[name])
        rows.append(row)
    return dict(pages=rows, labeled=totals)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", type=Path, help="directory containing the three source books")
    parser.add_argument("inspector")
    args = parser.parse_args()
    with TemporaryDirectory() as tmp:
        print(json.dumps(evaluate(args.sources, args.inspector, Path(tmp)), indent=2))
