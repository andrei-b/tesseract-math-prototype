# Inline math experiments for Tesseract 5.5.4

The native patch adds the boolean parameter `lstm_detect_subscripts`, default off. An English LSTM reader can enable it after initialization and inspect `ResultIterator::SymbolIsSubscript()` on each symbol. The recognized UTF-8 text, alternatives and boxes stay available to the caller. The experiment covers left-to-right horizontal text with short indices. It uses each symbol's height, distance from the preceding glyph and position relative to the row baseline. A narrow punctuation check handles some lowered digits that the model transcribes as a comma.

## Reproduce the native test

Apply the patch to an upstream checkout at tag `5.5.4`. The patch includes a Google Test in Tesseract's existing `ratngs_test` suite. The following Linux commands also exercise the public iterator with generated, self-authored lines. They require a C++ compiler, CMake, Leptonica development headers, English LSTM data, Python, Pillow and the DejaVu Serif regular and italic fonts.

```sh
# Run from this experiment directory. Set TESS_SRC to a checkout of tag 5.5.4.
git -C "$TESS_SRC" apply "$PWD/tesseract-5.5.4.patch"
cmake -S "$TESS_SRC" -B "$TESS_SRC/build" -DBUILD_SHARED_LIBS=ON -DBUILD_TRAINING_TOOLS=OFF
cmake --build "$TESS_SRC/build" --target tesseract -j4
c++ -std=c++17 inspect.cpp -I"$TESS_SRC/include" -I"$TESS_SRC/build/include" -L"$TESS_SRC/build" \
    -Wl,-rpath,"$TESS_SRC/build" -ltesseract $(pkg-config --cflags --libs lept) -o inspect
# Set TESSDATA_PREFIX to the directory containing eng.traineddata.
python3 test_fixture.py ./inspect
./inspect path/to/one-line.png --subscripts
```

The probe emits one line per OCR symbol with the glyph, four image-box coordinates, subscript flag, superscript flag, word and alternative/score pairs. It uses English, LSTM-only mode, single-line segmentation and choice mode 2. The fixture checks the placement of lowered digits, ordinary italic words, numeric text, punctuation and unlowered digits after capitals. Passing a separately built stock probe with `--stock` also checks that the default output matches 5.5.4.

## Real scan results

Stock 5.5.4 marked zero subscripts in these runs. The native patch gave the following results. A hit counts the placement of a printed character regardless of its OCR transcription. The identity column counts hits where the recognized character also matched the reference.

| Input | Printed subscripts | Placement hits | Hits with correct identity | False flags / other OCR symbols |
| --- | ---: | ---: | ---: | ---: |
| Photo of page 141 | 7 | 0 | 0 | 0 / 253 |
| Photo of page 149 | 16 | 1 | 0 | 1 / 712 |
| Earlier robotics scans, pages 116 and 186 | 7 | 1 | 0 | 0 / 59 |
| Additional 5p project lines | 5 | 1 | 1 | 0 / 337 |
| Additional computational chemistry lines | 30 | 2 | 1 | 0 / 147 |
| Previously unseen book, *Essays on the Theory of Numbers*, printed page 26 | 17 | 0 | 0 | 0 / 715 |

The first three rows were available during development. After fixing the rules, we evaluated the additional 5p and chemistry lines and a page from another book. Across those 33 lines the patch detected 3 of 52 printed subscripts (5.8%) and produced 0 false flags per 1,000 other OCR symbols (0 of 1,199). The two supplied photos alone yielded 1 of 23 placements and 1 false flag per 965 other symbols (1.04 per 1,000). These are selected lines from a few pages. They include real punctuation, numbers, italic prose and descenders. Recognition on a line Tesseract returned empty counts as a miss for every annotation on that line.

Both engines received identical pixels. The photo strips were rectified, enlarged and normalized for paper shading. A few lines on page 141 end at the edge of the photograph. Annotations mark printed glyph centers. The evaluator matches centers to OCR boxes one-to-one without using the predicted glyph or subscript flag. A split glyph can produce an extra box and a merged glyph can leave an annotation unmatched. The same stock and patched probes produced identical text, words, boxes, superscript flags and choices on the evaluated lines. The English model's SHA-256 was `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`.

For your own lines, supply a JSON list with an image path and a list of `[x_center, printed_character]` values for every subscript on that line. Include ordinary lines with an empty list. All coordinates are in the OCR input image.

```sh
python3 evaluate.py lines.json ./inspect --stock ./stock-inspect
```

To reproduce the independent book test from the matching DjVu edition, use DjVuLibre and the included page annotations.

```sh
python3 prepare_djvu_test.py ~/Downloads/Essays_on_the_Theory_of_Numbers.djvu /tmp/essays-lines
python3 evaluate.py /tmp/essays-lines/lines.json ./inspect --stock ./stock-inspect
```

On the earlier isolated robotics crop of italic z with subscript 2, the patched inspector returns `22` with only the second symbol flagged as a subscript. This illustrates the separation between placement and identity.

## Recovering missing glyphs before final word alignment

Enable `lstm_recover_subscripts=1` for recovery with the LSTM engine. It works on horizontal left-to-right text in single-line, single-block and automatic page segmentation (PSM 7, 6 and 3). Both recovery and the earlier placement pass are opt-in.

The layout filter can discard a complete equation before the LSTM sees it. On the chemistry test line its noise counters were 30 small marks and eight normal components. Recovery keeps a rejected row when it has repeated base-and-index shapes at comparable heights and baselines. When the decoder represents two isolated ink shapes as one letter or as a letter and two punctuation fragments, the patch rereads the two glyphs on a common baseline. It accepts a two-character result when the base agrees and the index passes the certainty check. The result iterator reports the original image coordinates. A letter followed by a single comma already accounts for two components and keeps its original transcription.

### Measured effect

All comparisons below use the same English model, pixels and segmentation mode. The baseline is the earlier placement patch enabled; the second run also enables ink recovery. Matches use the printed glyph centers. The first three rows together contain 56 prepared lines. The chemistry failure was a development case.

| Single-line input | Printed subscripts | Matched OCR boxes, before → after | Correct placement, before → after | Correct identity **and** placement, before → after | False flags, before → after |
| --- | ---: | ---: | ---: | ---: | ---: |
| 5p and chemistry | 35 | 21 → 31 | 3 → 5 | 2 → 3 | 0 → 0 |
| Book photos and earlier robotics scans | 30 | 29 → 29 | 2 → 4 | 0 → 2 | 1 → 1 |
| DjVu printed p.26 | 17 | 17 → 17 | 0 → 0 | 0 → 0 | 0 → 0 |
| DjVu printed p.62 | 21 | 18 → 18 | 6 → 6 | Unscored | 2 → 2 |
| DjVu printed p.63 | 5 | 5 → 5 | 0 → 0 | Unscored | 2 → 2 |

* The previously empty chemistry line produced 27 OCR symbols. Ten of 12 printed subscripts matched a box, two had the right character, and one had both the right character and placement. The complete equation still transcribed incorrectly.
* On the page 141 photo crop, `P,,` became P with a lowered n. The robotics scan had the same improvement for C with a lowered n. On the first 82 labeled subscripts, placement rose from 5 to 9 and correct identity plus placement rose from 2 to 5. There was one false flag in each run, among 2,223 and 2,238 other OCR symbols respectively.
* The DjVu p.62 check exposed a trial version changing a genuine comma after A. That example informed the single-comma guard. Printed p.63 was scored after fixing the guard. On both pages the oval subscripts were labeled for placement only.
* Automatic layout on both original photos, the complete chemistry scan and DjVu p.26 produced the same recognized text with recovery on and off. On the chemistry page one additional flag covered the printed pair of indices `nj` in one OCR box. Single-block mode also produced the same text on the chemistry page.

### Run recovery

```sh
./inspect path/to/line.png --subscripts --recover
./inspect path/to/page.png --auto --subscripts --recover
python3 compare_recovery.py lines.json ./inspect
python3 test_recovery.py ./inspect
python3 prepare_djvu_test.py ~/Downloads/Essays_on_the_Theory_of_Numbers.djvu /tmp/essays-p63 --printed-page 63
python3 compare_recovery.py /tmp/essays-p63/lines.json ./inspect
```

The generated regression includes a printed A with subscript 3 that the first pass reads as a single A. It checks both output characters, placement, coordinates and the recovered digit's alternative. It also covers a rejected equation, italic prose, a punctuation list, blank input, scattered speckles and a dotted rule.

## Document-specific z and 2

The separate Python reranker uses manually verified glyph boxes from one page of a book. It compares normalized ink masks only where Tesseract proposes both characters and chooses one of them. A close visual match and a margin over the other class are required. Widely separated OCR scores and runs of three or more letters trigger abstention. The CLI prints suggested changes with their word and bounding box. It needs NumPy and OpenCV and works with an unmodified Tesseract 5.5.4 probe.

We used three verified examples of each class on page 141 and evaluated seven printed italic z's and five true digits on page 149. Stock and reranked output both got 7 of 12 right. The reranker recovered zero letters and spoiled zero correctly recognized digits. Both alternatives appeared at four labeled positions. For the inline z that stock read as 2, the respective scores were 20.35 and 93.39, outside the reranker's 25-point window. These scores are native choice scores. The measured sample gives no evidence for enabling this correction automatically.

Use a reference manifest like `[{"image":"page-1.png","glyphs":[["z",[10,20,25,40]],["2",[40,20,55,40]]]}]`. Coordinates are left, top, right and bottom with the last two exclusive. For evaluation add a `z2` list of `[x_center, printed_character]` values to each test line and keep test pages out of the reference bank.

```sh
python3 rerank.py references.json ./inspect path/to/one-line.png
python3 evaluate_choices.py references.json test-lines.json ./inspect
python3 -m unittest test_rerank
```
