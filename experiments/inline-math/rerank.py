"""Suggest z/2 changes in a line using verified glyph boxes from the same book."""
import argparse
import json
from pathlib import Path
import re
import cv2
import numpy as np
from symbols import read_symbols


def shape(gray, box):
    l, t, r, b = box
    if not (0 <= l < r <= gray.shape[1] and 0 <= t < b <= gray.shape[0]):
        raise ValueError(f"Box {box} is outside the image")
    patch = gray[t:b, l:r]
    if patch.size < 4 or patch.max() == patch.min():
        return None
    _, mask = cv2.threshold(patch, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    x, y, w, h = cv2.boundingRect(mask)
    if w < 2 or h < 2:
        return None
    scale = 28 / max(w, h)
    resized = cv2.resize(mask[y:y+h, x:x+w], (max(1, round(w*scale)), max(1, round(h*scale))),
                         interpolation=cv2.INTER_AREA)
    canvas = np.zeros((32, 32), dtype=np.float32)
    h, w = resized.shape
    x, y = (32-w)//2, (32-h)//2
    canvas[y:y+h, x:x+w] = resized / 255.0
    return canvas


def load_gray(path):
    image = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise ValueError(f"Cannot open {path}")
    return image


def templates(manifest):
    bank = {"z": [], "2": []}
    for page in json.loads(manifest.read_text()):
        image = load_gray(manifest.parent / page["image"])
        for label, box in page["glyphs"]:
            sample = shape(image, box)
            if label not in bank or sample is None:
                raise ValueError(f"Invalid reference {label!r} at {box}")
            bank[label].append(sample)
    if any(not examples for examples in bank.values()):
        raise ValueError("Provide verified examples of both z and 2")
    return bank


def suggestion(symbol, gray, bank):
    top = symbol.text
    if top not in bank or not bank.keys() <= symbol.choices.keys():
        return top
    if re.search(r"[^\W\d_]{3}", symbol.word.replace("2", "z")):
        return top
    other = "2" if top == "z" else "z"
    if symbol.choices[top] - symbol.choices[other] > 25:
        return top
    glyph = shape(gray, symbol.box)
    if glyph is None:
        return top
    distances = {c: min(float(np.abs(glyph - ref).mean()) for ref in refs)
                 for c, refs in bank.items()}
    if distances[other] < 0.20 and distances[other] + 0.04 < distances[top]:
        return other
    return top


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("templates", type=Path)
    parser.add_argument("inspector")
    parser.add_argument("image", type=Path)
    args = parser.parse_args()
    bank = templates(args.templates)
    gray = load_gray(args.image)
    changes = []
    for symbol in read_symbols(args.inspector, args.image):
        new = suggestion(symbol, gray, bank)
        if new != symbol.text:
            changes.append(dict(word=symbol.word, box=symbol.box, before=symbol.text, after=new))
    print(json.dumps(changes, indent=2))
