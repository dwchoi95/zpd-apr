#!/usr/bin/env bash
# The RQ1 problems' trajectories that never reach acceptance (never-accepted-20261026-v1): every submission executed
# on the benchmark's test suites with the benchmark's runner settings, so that the students' steps can be described
# beyond the trajectories that end in acceptance. Execution only; no model runs.
set -euo pipefail

WORK_ROOT=/home/cdw/VSCode/zpd-apr
SRC=${WORK_ROOT}/.runtime/never-accepted-20261026-v1/source
PYTHON=${WORK_ROOT}/.runtime/fse-env/bin/python
FAMILY=${WORK_ROOT}/outputs/never-accepted-20261026
DATA=${FAMILY}/data
CACHE=${FAMILY}/outcomes/test.jsonl
WORKERS=16   # the benchmark's heavy tests time out under more parallel load

exec >>"${FAMILY}/pipeline.log" 2>&1
cd "${SRC}"
export PYTHONPATH=.
log() { echo "[$(date --iso-8601=seconds)] $*"; }
log "Source $(cat SOURCE_COMMIT); $(wc -l < "${DATA}/splits/test.jsonl") trajectories"
if ! grep -q '"outcome_cache_complete": true' "${CACHE%.jsonl}.summary.json" 2>/dev/null; then
  "${PYTHON}" run.py build-outcome-cache --data-root "${DATA}" --split test --output "${CACHE}" \
    --workers "${WORKERS}" --case-workers 1 --timeout-sec 2.5
fi
grep -q '"outcome_cache_complete": true' "${CACHE%.jsonl}.summary.json"
touch "${FAMILY}/COMPLETE"
log "Never-accepted execution complete"
