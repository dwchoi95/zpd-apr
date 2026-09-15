#!/usr/bin/env bash
set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
PYTHON=/home/cdw/VSCode/zpd-apr/.runtime/fse-env/bin/python
"$PYTHON" -m unittest discover -s tests -p 'test_zpd_history*'
"$PYTHON" -m scripts.zpd_history_selection \
  --input outputs/zpd-history-gate-20260915/prepared-inputs \
  --power outputs/zpd-history-gate-20260915/power-results-v1 \
  --protocol analysis_protocols/zpd-history-implementation-20260915.md \
  --output selection-results
