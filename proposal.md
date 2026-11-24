# Add an opt-in equation recognition mode with LaTeX output

Scientific book scans contain expressions whose meaning depends on the positions of symbols. For example, a fraction bar separates an expression above it from an expression below it, and a raised or lowered character can be attached to a base. OCR clients need a transcription that preserves those relationships.

Tesseract has a legacy equation detector that can label a region as an equation. Its LSTM recognizer decodes a line image into words. I propose an opt-in recognizer that takes one cropped, printed equation and returns LaTeX. [Equation detector](https://github.com/tesseract-ocr/tesseract/blob/main/src/ccmain/equationdetect.cpp) · [LSTM recognizer](https://github.com/tesseract-ocr/tesseract/blob/main/src/lstm/lstmrecognizer.cpp)

## Reproduction with plain Tesseract

On Ubuntu 24.04 x86-64, Tesseract 5.3.4 with the installed English model recognized 2 of 8 synthetic equations correctly. The sheet contains one centered expression per page. It can be downloaded or regenerated from the public fixture. [Fixture PDF](https://github.com/andrei-b/YAGF/blob/2af1c1e7caba963e1e2a72aa80a1bd49c99ed804/tests/data/math/equations.pdf) · [LaTeX source](https://github.com/andrei-b/YAGF/blob/2af1c1e7caba963e1e2a72aa80a1bd49c99ed804/tests/data/math/equations.tex)

```sh
pdftoppm -r 300 -png equations.pdf formula
tesseract formula-4.png stdout -l eng --dpi 300
tesseract formula-6.png stdout -l eng --dpi 300
```

Page 4 contains `x^{2}+1=10` and produced `xv? +1=10`. Page 6 contains `\frac{1}{2}+\frac{1}{4}=\frac{3}{4}` and produced empty output. This baseline was measured with 5.3.4. A [5.5.4 release](https://github.com/tesseract-ocr/tesseract/releases/tag/5.5.4) reproduction remains useful before opening a formal issue.

## Proposed first patch

Take an explicit equation crop, including a rectangle supplied by an application. Find connected components and retain their two-dimensional bounds. Use glyph readings from Tesseract and spatial rules to identify the baseline, attach scripts, group numerators and denominators around a fraction bar, and recover the area covered by a radical. Serialize the resulting structure to LaTeX. An unresolved result should be explicit.

The first patch would prioritize isolated, printed expressions with single-character superscripts and subscripts, simple fractions, and square roots. A later patch could detect formulas on mixed pages and preserve their positions in the document reading order. I would welcome guidance on the appropriate CLI and library entry points before proposing a public API. [Existing rectangle and connected-component APIs](https://github.com/tesseract-ocr/tesseract/blob/main/include/tesseract/baseapi.h)

## Local proof of concept

A standalone Python experiment uses OpenCV to group the components and calls Tesseract to transcribe isolated glyphs. It recognized seven equations on the eight-example development sheet. The summation was unresolved. The prototype was tuned on this sheet. On a separate set of four synthetic expressions in the same typesetting style, it recognized three and left a second radical unresolved. This establishes that the geometric path is worth testing on a broader corpus.

```sh
./test-local.sh
./test-local.sh --validation
```

The scripts use Poppler and Tesseract with the English language model. Validation also uses pdfLaTeX. The runner uses YAGF's local math environment when present and `python3` otherwise. Set `YAGF_FORMULA_PYTHON` to a Python environment with OpenCV and NumPy if needed. Outside the YAGF checkout, the runner downloads the pinned public fixture with curl. Set `YAGF_FORMULA_FIXTURE` to use a local copy. Pass a single cropped equation PNG to `formula.py` to try your own image.

## Tests for an upstream patch

- Score complete equation structure on examples held out by document and typeface. Tolerate harmless LaTeX spacing or grouping differences.
- Count wrong structures and unresolved formulas separately. Include script attachment, fraction-versus-minus distinctions, nested groups, and radicals with descenders.
- Cover blank and unsupported inputs. Verify that ordinary OCR output stays the same when equation recognition is disabled.
- Measure extra CPU time per formula. For a later mixed-page patch, measure false detections on ordinary italic prose, true digits, and punctuation.

Is there interest in reviewing an experimental equation recognition path with this scope? I can share the synthetic fixtures and the proof of concept for discussion. [Tesseract developer forum](https://groups.google.com/g/tesseract-dev) · [Contribution guide](https://github.com/tesseract-ocr/tesseract/blob/main/CONTRIBUTING.md)
