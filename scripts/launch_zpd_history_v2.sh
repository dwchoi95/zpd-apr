#!/usr/bin/env bash
set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
PYTHON=/home/cdw/VSCode/zpd-apr/.runtime/fse-env/bin/python
"$PYTHON" -m unittest discover -s tests -p 'test_zpd_history*'
"$PYTHON" -m scripts.zpd_history_v2_development \
  --input outputs/zpd-history-gate-20260915/prepared-inputs \
  --baseline-selection outputs/zpd-history-gate-20260915/selection-results-v1 \
  --power outputs/zpd-history-gate-20260915/power-results-v1 \
  --power-protocol analysis_protocols/zpd-history-implementation-20260915.md \
  --protocol analysis_protocols/zpd-history-v2-development-plan-20260916.md \
  --output development-results
