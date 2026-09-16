#!/usr/bin/env bash
set -euo pipefail
# Isolated bundle root only. The lock is global to this fixed cohort, not this run.
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
PYTHON=/home/cdw/VSCode/zpd-apr/.runtime/fse-env/bin/python
"$PYTHON" -m unittest discover -s tests -p 'test_zpd_history*'
"$PYTHON" -m scripts.zpd_history_test \
  --input outputs/zpd-history-gate-20260915/prepared-inputs \
  --selection outputs/zpd-history-gate-20260915/selection-results-v1 \
  --power outputs/zpd-history-gate-20260915/power-results-v1 \
  --protocol analysis_protocols/zpd-history-implementation-20260915.md \
  --test-protocol analysis_protocols/zpd-history-test-stage-20260916.md \
  --lock /home/cdw/VSCode/zpd-apr/outputs/zpd-history-gate-20260915/TEST_CONSUMED.json \
  --output test-results
"$PYTHON" -m scripts.zpd_history_inference \
  --predictions test-results \
  --prepared outputs/zpd-history-gate-20260915/prepared-inputs \
  --output inference-results
