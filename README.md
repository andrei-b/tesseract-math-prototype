# Tesseract math prototype

A CPU experiment that converts one cropped, printed equation to LaTeX. It uses Tesseract to identify glyphs and their image geometry to reconstruct superscripts, subscripts, simple fractions, and square roots.

This is a standalone prototype for the [upstream proposal](proposal.md). Its scope is clean, isolated equations. Recognition can return an unresolved result or misread a glyph.

## Run the comparison

Install Tesseract with English language data, Python 3, curl, and Poppler's `pdftoppm`. The second test sheet also requires `pdflatex` with the LaTeX `geometry` package.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install numpy opencv-python-headless
YAGF_FORMULA_PYTHON=.venv/bin/python ./test-local.sh
YAGF_FORMULA_PYTHON=.venv/bin/python ./test-local.sh --validation
```

Both runs print plain Tesseract output followed by the prototype's LaTeX. The first runner fetches a pinned, public [YAGF fixture](https://github.com/andrei-b/YAGF/blob/2af1c1e7caba963e1e2a72aa80a1bd49c99ed804/tests/data/math/equations.pdf) when a local copy is unavailable. The second renders [four separate synthetic equations](validation.tex). To try your own input, run:

```sh
.venv/bin/python formula.py path/to/equation.png
```

## Initial results

With Tesseract 5.3.4, plain OCR correctly read two of eight equations on the development sheet. The prototype read seven and left a summation unresolved. It then read three of four equations on a separate sheet in the same typeface and left one radical unresolved. These are small synthetic sets. The development sheet informed the geometry rules.
