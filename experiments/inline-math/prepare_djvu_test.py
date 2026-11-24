"""Extract manually labeled lines from three printed pages of Essays on the Theory of Numbers."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageOps

# Center y and subscript x coordinates on a preview 880 pixels wide.
LINES = [
    (554, []), (591, []), (628, [(178, "2"), (428, "2")]), (664, [(624, "2")]),
    (701, [(213, "1"), (713, "2")]), (737, [(143, "1")]), (773, []),
    (810, [(294, "2"), (585, "1")]), (846, [(286, "2")]), (883, [(496, "1"), (543, "2")]),
    (918, []), (955, []), (992, [(719, "1")]), (1028, [(132, "2"), (655, "2")]),
    (1065, [(376, "2")]), (1101, [(720, "2")]), (1137, [(339, "2")]),
]
SOURCE_SHA256 = "5137ac0ed813974489581103b43897679145e7a39932e4fa2a38047f1339cf5e"


# Later pages were annotated for placement only. Each mark is a visually
# lowered oval in this edition; identity is deliberately left unscored.
def placement_lines(rows):
    return [(y, [(x, None) for x in centers]) for y, centers in rows]


PAGES = {
    26: (31, 88, 744, 16, LINES),
    62: (65, 86, 735, 15, placement_lines([
        (115, []), (152, [357]), (188, []), (224, []), (260, []), (296, []), (332, []),
        (368, []), (405, []), (441, [167, 210, 251]), (477, []), (513, []), (550, []),
        (586, [392, 435, 476]), (622, []), (657, [391]), (698, []), (734, []), (770, [378]),
        (806, [292, 334, 377, 591]), (841, []), (867, [440]), (909, []), (945, [486]),
        (981, []), (1018, [248, 291, 333]), (1054, []), (1091, []), (1126, [368, 411, 454]),
    ])),
    63: (66, 143, 831, 16, placement_lines([
        (125, []), (163, []), (201, [278]), (240, []), (279, []), (317, []), (356, []),
        (394, [184]), (433, [710]), (472, [292, 550]), (511, []), (548, []), (588, []),
        (626, []), (680, []), (727, []), (774, []), (813, []), (851, []),
        (889, []), (927, []), (966, []), (1005, []),
    ])),
}


def prepare(source, output, printed_page=26):
    if hashlib.sha256(source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("The annotations require the matching DjVu edition (see SOURCE_SHA256)")
    number, x1, x2, top_margin, annotations = PAGES[printed_page]
    pixels = subprocess.check_output(["ddjvu", "-format=pgm", "-scale=300", f"-page={number}", str(source), "-"])
    page = Image.open(io.BytesIO(pixels))
    scale = page.width / 880
    left = round(x1 * scale)
    output.mkdir(exist_ok=True, parents=True)
    lines = []
    for i, (y, labels) in enumerate(annotations, start=1):
        strip = page.crop((left, round((y - top_margin) * scale), round(x2 * scale), round((y + 17) * scale)))
        path = output / f"essays-{i:02d}.png"
        ImageOps.expand(strip, border=10, fill=255).save(path)
        centers = [[round(x * scale) - left + 10, c] for x, c in labels]
        lines.append(dict(image=path.name, subscripts=centers))
    (output / "lines.json").write_text(json.dumps(lines, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--printed-page", type=int, choices=sorted(PAGES), default=26)
    args = parser.parse_args()
    prepare(args.source, args.output, args.printed_page)
