"""Read Tesseract's symbol iterator and match single-line image annotations."""
from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess


@dataclass
class Symbol:
    text: str
    box: tuple
    sub: bool
    sup: bool
    word: str
    choices: dict


def read_symbols(inspector, image, enabled=False, recover=False, layout="line"):
    cmd = [str(Path(inspector).resolve()), str(image)]
    if enabled:
        cmd.append("--subscripts")
    if layout != "line":
        cmd.append("--" + layout)
    if recover:
        cmd.append("--recover")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{cmd} returned {result.returncode}: {result.stderr}")
    symbols = []
    for line in result.stdout.splitlines():
        text, l, t, r, b, sub, sup, word, *pairs = shlex.split(line)
        choices = {c: float(v) for c, v in zip(pairs[::2], pairs[1::2])}
        symbols.append(Symbol(text, tuple(map(int, (l, t, r, b))), sub == "1",
                              sup == "1", word, choices))
    return symbols


def match_centers(annotations, symbols):
    """Match labeled ink centers to individual OCR boxes, independent of text or flags."""
    candidates = []
    for i, (x, _) in enumerate(annotations):
        for j, symbol in enumerate(symbols):
            l, t, r, b = symbol.box
            distance = abs(x - (l + r) / 2)
            if l - 1 <= x <= r + 1 and distance <= max(3, (b - t) * 0.45):
                candidates.append((distance, i, j))
    matches = {}
    used = set()
    for _, i, j in sorted(candidates):
        if i not in matches and j not in used:
            matches[i] = j
            used.add(j)
    return matches
