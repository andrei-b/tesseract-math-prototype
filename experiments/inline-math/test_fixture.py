"""Render original regression lines and exercise the public iterator end to end."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from PIL import Image, ImageDraw, ImageFont
from evaluate import evaluate


def render(output):
    normal = ImageFont.truetype("DejaVuSerif.ttf", 48)
    italic = ImageFont.truetype("DejaVuSerif-Italic.ttf", 48)
    small = ImageFont.truetype("DejaVuSerif.ttf", 32)
    lines = [
        [("Points P", normal, 0), ("1", small, 10), (" and P", normal, 0),
         ("2", small, 10), (" lie on the curve.", normal, 0)],
        [("Compare C", normal, 0), ("n", small, 10), (" with A", normal, 0),
         ("m", small, 10), (" in this graph.", normal, 0)],
        [("The quick glyphs dip gently, by and by.", italic, 0)],
        [("Page 25, line 12. At 2 pm we read 2026.", normal, 0)],
        [("For P, Q; R: and F. the punctuation stays ordinary.", normal, 0)],
        [("Chapter P1 and point P2 appear in Fig. 3.", normal, 0)],
    ]
    manifest = []
    for i, runs in enumerate(lines):
        image = Image.new("L", (1600, 120), 255)
        draw = ImageDraw.Draw(image)
        x = 25
        centers = []
        for string, font, offset in runs:
            draw.text((x, 78+offset), string, font=font, fill=0, anchor="ls")
            if offset:
                l, _, r, _ = draw.textbbox((x, 78+offset), string, font=font, anchor="ls")
                centers.append([(l+r)/2, string])
            x += round(draw.textlength(string, font=font))
        path = output / f"line-{i}.png"
        image.crop((0, 0, x+25, image.height)).save(path)
        manifest.append(dict(image=path.name, subscripts=centers))
    path = output / "lines.json"
    path.write_text(json.dumps(manifest, indent=2))
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inspector")
    parser.add_argument("--stock")
    parser.add_argument("--save", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory() as tmp:
        out = args.save or Path(tmp)
        out.mkdir(parents=True, exist_ok=True)
        result = evaluate(render(out), args.inspector, args.stock)
        print(json.dumps(result, indent=2))
        counts = result["totals"]
        digit_line = result["lines"][0]["counts"]
        if (counts["baseline_tp"] or counts["baseline_fp"] or counts["fp"] or
                digit_line["tp"] != digit_line["positives"]):
            raise SystemExit("Subscript regression failed")
