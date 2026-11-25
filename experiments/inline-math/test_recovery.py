"""Regression tests for early row rejection and local glyph rereading with English 5.5.4."""
import argparse
from pathlib import Path
import random
from tempfile import TemporaryDirectory
from PIL import Image, ImageDraw, ImageFont
from symbols import read_symbols


def draw_run(draw, x, baseline, text, font):
    draw.text((x, baseline), text, font=font, anchor="ls", fill=0)
    return round(draw.textlength(text, font=font))


def merged_line(path):
    body = ImageFont.truetype("DejaVuSans.ttf", 36)
    small = ImageFont.truetype("DejaVuSans.ttf", 16)
    image = Image.new("L", (1800, 90), 255)
    draw = ImageDraw.Draw(image)
    x = 24
    for base, sub in zip("PTCBKAEQRFBLSM", "123n233m2mn12n"):
        left = x
        x += draw_run(draw, x, 55, base, body) - 2
        x += draw_run(draw, x, 58, sub, small)
        if base == "A":
            target = (left, x)
        x += 29
    image.crop((0, 0, x, 90)).save(path)
    return target


def bracketed_line(path):
    fonts = {h: ImageFont.truetype("DejaVuSerif.ttf", h) for h in (75, 22, 14)}
    image = Image.new("L", (700, 150), 255)
    draw = ImageDraw.Draw(image)
    x = 12
    for i, (base, sub) in enumerate(zip("TEPAC", "nj2mn")):
        if i % 2 == 0:
            x += draw_run(draw, x, 85, "(", fonts[75]) + 2
        x += draw_run(draw, x, 70, base, fonts[22]) + 2
        x += draw_run(draw, x, 79, sub, fonts[14]) + 2
        if i % 2 == 0:
            x += draw_run(draw, x, 85, ")", fonts[75]) + 2
        if i < 4:
            x += draw_run(draw, x, 70, "+", fonts[22]) + 2
    image.crop((0, 0, x + 12, 150)).save(path)


def lowered_digits(path):
    body = ImageFont.truetype("DejaVuSerif.ttf", 40)
    small = ImageFont.truetype("DejaVuSerif.ttf", 24)
    image = Image.new("L", (750, 100), 255)
    draw = ImageDraw.Draw(image)
    x = 18
    for base, sub in zip("PCABR", "12321"):
        x += draw_run(draw, x, 62, base, body) + 2
        x += draw_run(draw, x, 67, sub, small) + 30
    draw_run(draw, x, 62, "are points.", body)
    image.crop((0, 0, x + 230, 100)).save(path)


def check(inspector, directory):
    path = directory / "line.png"
    left, right = merged_line(path)

    def target(recover):
        return [s for s in read_symbols(inspector, path, enabled=True, recover=recover)
                if left <= (s.box[0] + s.box[2]) / 2 < right]

    old = target(False)
    new = target(True)
    assert [s.text for s in old] == ["A"]
    assert [(s.text, s.sub) for s in new] == [("A", False), ("3", True)]
    assert new[1].box[3] > new[0].box[3] and "3" in new[1].choices

    lowered_digits(path)
    old = read_symbols(inspector, path, enabled=True, recover=True)
    new = read_symbols(inspector, path, enabled=True, recover=True, reread=True)
    assert len(new) == len(old)
    assert [(o.word, n.word) for o, n in zip(old, new) if o.text != n.text] == [
        ("P;", "P1"), ("R,", "R1")
    ]
    for o, n in zip(old, new):
        assert tuple(o.box) == tuple(n.box)
        if o.text != n.text:
            assert n.sub and n.text in n.choices and n.word.endswith(n.text)
        elif n.word in ("are", "points."):
            assert o == n

    bracketed_line(path)
    assert not read_symbols(inspector, path)
    assert len(read_symbols(inspector, path, recover=True)) >= 5

    for kind in ("blank", "speckles", "dotted-rule", "italic", "punctuation"):
        image = Image.new("L", (800, 90), 255)
        draw = ImageDraw.Draw(image)
        if kind == "speckles":
            rng = random.Random(131)
            for _ in range(240):
                x, y = rng.randrange(8, 790), rng.randrange(4, 78)
                draw.ellipse((x, y, x + 2, y + 2), fill=0)
        elif kind == "dotted-rule":
            for x in range(10, 790, 7):
                draw.ellipse((x, 40, x + 2, 42), fill=0)
        elif kind == "italic":
            font = ImageFont.truetype("DejaVuSerif-Italic.ttf", 36)
            draw_run(draw, 12, 55, "By my desk lay page 25, line 2.", font)
        elif kind == "punctuation":
            font = ImageFont.truetype("DejaVuSerif-Italic.ttf", 36)
            draw_run(draw, 12, 55, "A, B, C, and D are four points.", font)
        image.save(path)
        before = read_symbols(inspector, path, enabled=True)
        after = read_symbols(inspector, path, enabled=True, recover=True)
        assert before == after, kind
        assert after == read_symbols(inspector, path, enabled=True, recover=True, reread=True), kind


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inspector")
    args = parser.parse_args()
    with TemporaryDirectory() as tmp:
        check(args.inspector, Path(tmp))
    print("Row recovery, merged glyph, word and noise regressions passed.")
