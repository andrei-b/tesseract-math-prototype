#!/usr/bin/env bash
set -euo pipefail
proposal_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
fixture="${YAGF_FORMULA_FIXTURE:-$proposal_dir/../../tests/data/math/equations.pdf}"
local_python="${XDG_DATA_HOME:-$HOME/.local/share}/yagf2/math-ocr/venv/bin/python"
python_bin="${YAGF_FORMULA_PYTHON:-python3}"
if [[ -z ${YAGF_FORMULA_PYTHON:-} && -x $local_python ]]; then
    python_bin="$local_python"
fi
work_dir=$(mktemp -d)
trap 'rm -rf -- "$work_dir"' EXIT
if [[ ${1:-} == --validation ]]; then
    pdflatex -halt-on-error -interaction=nonstopmode -output-directory="$work_dir" \
        "$proposal_dir/validation.tex" > "$work_dir/pdflatex.log"
    fixture="$work_dir/validation.pdf"
elif [[ ! -f $fixture && -z ${YAGF_FORMULA_FIXTURE:-} ]]; then
    fixture="$work_dir/equations.pdf"
    curl -fsSL https://raw.githubusercontent.com/andrei-b/YAGF/2af1c1e7caba963e1e2a72aa80a1bd49c99ed804/tests/data/math/equations.pdf \
        -o "$fixture"
fi
pdftoppm -r 300 -png "$fixture" "$work_dir/formula"
printf 'Plain Tesseract\n'
for image in "$work_dir"/formula-*.png; do
    baseline=$(OMP_THREAD_LIMIT=1 tesseract "$image" stdout -l eng --dpi 300 2>/dev/null)
    printf '%s\t%s\n' "$(basename "$image")" "${baseline:-[no text]}"
done
printf '\nExperimental formula recognition\n'
"$python_bin" "$proposal_dir/formula.py" "$work_dir"/formula-*.png
