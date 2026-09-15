#!/usr/bin/env bash
set -euo pipefail
# Run from the isolated, checksum-verified bundle root, never the live checkout.
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
PYTHON=/home/cdw/VSCode/zpd-apr/.runtime/fse-env/bin/python
"$PYTHON" -m unittest discover -s tests -p 'test_zpd_history*'
"$PYTHON" -m scripts.run_zpd_history_gate power \
  --input outputs/zpd-history-gate-20260915/prepared-inputs \
  --protocol analysis_protocols/zpd-history-implementation-20260915.md \
  --output power-results
