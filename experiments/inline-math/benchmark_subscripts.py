"""Compare stock, published and revised recognition on identical pages and count child CPU time."""
import argparse
from collections import Counter
from difflib import SequenceMatcher
import json
import os
from pathlib import Path
import resource
from statistics import median
from tempfile import TemporaryDirectory

from PIL import Image
from evaluate_reread_pages import labeled_scores, render
from symbols import read_symbols


def cpu_seconds():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def edits(before, after):
    a = [s.text for s in before]
    b = [s.text for s in after]
    changes = SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if a != b else []
    return [dict(before="".join(a[i:j]), after="".join(b[k:l]),
                 old_boxes=[s.box for s in before[i:j]], new_boxes=[s.box for s in after[k:l]])
            for op, i, j, k, l in changes if op != "equal"]


def benchmark(sources, probes, directory):
    pages = json.loads(Path(__file__).with_name("cross-book-subscripts.json").read_text())
    stages = list(probes)
    results = []
    totals = {stage: Counter() for stage in stages}
    for index, page in enumerate(pages):
        path = directory / page["image"]
        render(sources / page["source"], page["page"], path)
        with Image.open(path) as image:
            if list(image.size) != page["size"]:
                raise ValueError(f"Unexpected page dimensions for {path.name}")
        output = {}
        seconds = {stage: [] for stage in stages}
        for trial in range(3):
            first = (index + trial) % len(stages)
            for stage in stages[first:] + stages[:first]:
                flags = stage != "stock"
                start = cpu_seconds()
                symbols = read_symbols(probes[stage], path, enabled=flags, recover=flags,
                                       layout="auto", reread=flags, language=page["lang"], best_only=True)
                seconds[stage].append(cpu_seconds() - start)
                if stage in output and output[stage] != symbols:
                    raise ValueError(f"Recognition changed between trials for {stage} on {path.name}")
                output[stage] = symbols
        scores = {}
        for stage in stages:
            scores[stage] = labeled_scores(page["subscripts"], output[stage])
            totals[stage].update(scores[stage])
            totals[stage]["cpu_seconds"] += median(seconds[stage])
            totals[stage]["symbols"] += len(output[stage])
            if page["ordinary_control"]:
                totals[stage]["control_symbols"] += len(output[stage])
                totals[stage]["control_subscript_flags"] += sum(s.sub for s in output[stage])
        results.append(dict(image=path.name, ordinary_control=page["ordinary_control"],
                            scores=scores, cpu_seconds=seconds, edits={
                                f"{first}_to_{last}": edits(output[first], output[last])
                                for first, last in [("stock","published"), ("published","revised"),
                                                    ("stock","revised")]}))
    return dict(totals=totals, pages=results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", type=Path)
    for engine in ("stock", "published", "revised"):
        parser.add_argument(engine, help="inspector linked to this engine")
    args = parser.parse_args()
    os.environ["OMP_THREAD_LIMIT"] = "1"
    with TemporaryDirectory() as tmp:
        print(json.dumps(benchmark(args.sources, {stage: getattr(args, stage)
                         for stage in ("stock", "published", "revised")}, Path(tmp)), indent=2,
                         ensure_ascii=False))
