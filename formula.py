#!/usr/bin/env python3
"""CPU experiment for recognizing a single printed equation from a PNG."""

from argparse import ArgumentParser
from dataclasses import dataclass
from statistics import median
import os
import re
import subprocess
from pathlib import Path

import cv2
import numpy as np


class UnsupportedFormula(Exception):
    pass


@dataclass(frozen=True)
class Glyph:
    x: int
    y: int
    width: int
    height: int
    label: int

    @property
    def right(self):
        return self.x + self.width

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def center(self):
        return self.x + self.width / 2


def read_glyph(glyph, labels):
    pixels = labels[glyph.y:glyph.bottom, glyph.x:glyph.right] == glyph.label
    image = np.where(pixels, 0, 255).astype(np.uint8)
    scale = 48 / glyph.height
    image = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
    image = cv2.copyMakeBorder(image, 16, 16, 16, 16, cv2.BORDER_CONSTANT, value=255)
    _, png = cv2.imencode(".png", image)
    args = [
        "tesseract", "stdin", "stdout", "--dpi", "300", "--psm", "13", "-l", "eng",
        "-c", "tessedit_char_whitelist=0123456789abcdefghijklmnopqrstuvwxyz+<>",
    ]
    result = subprocess.run(
        args, input=png.tobytes(), capture_output=True, check=True, timeout=10,
        env={**os.environ, "OMP_THREAD_LIMIT": "1"},
    ).stdout.decode().strip()
    if not re.fullmatch(r"[0-9a-z+<>]", result):
        raise UnsupportedFormula("Tesseract did not read a single supported glyph")
    return result


def parse(glyphs, labels, depth=0):
    heights = [g.height for g in glyphs if g.height >= 8]
    if not heights or depth > 4:
        raise UnsupportedFormula("Empty expression or unsupported nesting")
    height = median(heights)
    remaining = glyphs.copy()
    tokens = []
    bars = [g for g in glyphs if g.width >= 3.5 * g.height and g.height < height * 0.22]
    for bar in bars:
        if bar not in remaining:
            continue
        matching = [
            g for g in bars if g in remaining
            and abs(g.x - bar.x) < height * 0.15 and abs(g.right - bar.right) < height * 0.15
            and bar.bottom < g.y < bar.bottom + height * 0.36
        ]
        if matching:
            second = min(matching, key=lambda g: g.y)
            remaining.remove(bar)
            remaining.remove(second)
            tokens.append((bar, "=", False))

    for bar in bars:
        if bar not in remaining:
            continue
        aligned = [
            g for g in remaining if g not in bars and bar.x <= g.center <= bar.right
            and g.width <= bar.width * 1.1
        ]
        above = [g for g in aligned if 0 <= bar.y - g.bottom <= height * 0.8]
        below = [g for g in aligned if 0 <= g.y - bar.bottom <= height * 0.8]
        remaining.remove(bar)
        if above and below:
            numerator = parse(above, labels, depth + 1)
            denominator = parse(below, labels, depth + 1)
            tokens.append((bar, r"\frac{%s}{%s}" % (numerator, denominator), False))
            for glyph in above + below:
                remaining.remove(glyph)
        else:
            tokens.append((bar, "-", False))

    for root in remaining.copy():
        if root not in remaining or root.width < 2.5 * root.height:
            continue
        mask = labels[root.y:root.bottom, root.x:root.right] == root.label
        top = mask[:max(1, root.height // 6)]
        row = top[top.sum(axis=1).argmax()]
        columns = np.flatnonzero(row)
        if columns.size < root.width * 0.55 or columns[0] < root.width * 0.10:
            continue
        start = root.x + columns[0]
        # Operators already grouped above can occur inside a radical too.
        inside = [g for g in remaining if g != root and start - 4 <= g.center <= root.right
                  and root.y <= g.y and g.bottom <= root.bottom + height * 0.15]
        if not inside:
            continue
        tokens.append((root, r"\sqrt{%s}" % parse(inside, labels, depth + 1), False))
        for glyph in [root, *inside]:
            remaining.remove(glyph)

    if remaining:
        baseline = max((g.bottom for g in remaining), key=lambda base: sum(
            g.height for g in remaining if abs(g.bottom - base) <= height * 0.07
        ))
        for glyph in remaining:
            if glyph.height < height * 0.32 or glyph.height > height * 1.55:
                raise UnsupportedFormula("A component falls outside the simple printed-glyph range")
            tokens.append((glyph, read_glyph(glyph, labels), True))
    else:
        baseline = 0

    parts = []
    previous = None
    for box, value, plain in sorted(tokens, key=lambda item: item[0].x):
        if plain and previous and previous[1].isalnum() and value.isalnum():
            gap = box.x - previous[0].right
            if -height * 0.08 <= gap < height * 0.38:
                if box.bottom < baseline - height * 0.23:
                    value = "^{" + value + "}"
                elif box.bottom > baseline + height * 0.16 and box.y >= previous[0].y + height * 0.18:
                    value = "_{" + value + "}"
        parts.append(value)
        previous = (box, value)
    return "".join(parts)


def recognize(path):
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None or image.size > 4_000_000:
        raise UnsupportedFormula("Use a readable, small, single-equation image")
    _, labels, stats, _ = cv2.connectedComponentsWithStats((image < 170).astype(np.uint8), 8)
    glyphs = [
        Glyph(*map(int, box[:4]), index)
        for index, box in enumerate(stats[1:], start=1) if box[4] >= 8
    ]
    if not 1 <= len(glyphs) <= 48 or not any(g.height >= 8 for g in glyphs):
        raise UnsupportedFormula("Expected a single printed equation with visible ink")
    return parse(glyphs, labels)


def main():
    cli = ArgumentParser(description=__doc__)
    cli.add_argument("images", nargs="+", type=Path)
    args = cli.parse_args()
    for path in args.images:
        try:
            text = recognize(path)
        except (UnsupportedFormula, subprocess.SubprocessError, OSError) as error:
            text = f"[unresolved] {error}"
        print(f"{path.name}\t{text}", flush=True)


if __name__ == "__main__":
    main()
