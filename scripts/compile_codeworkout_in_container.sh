#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR=${1:-/sources}
STATUS_DIR=${2:-/status}
WORKERS=${3:-32}
mkdir -p "${STATUS_DIR}"

compile_one() {
  local source=$1 status_dir=$2
  local filename id status tmpdir rc compiles
  filename=${source##*/}
  id=${filename%.java}
  status=${status_dir}/${id}.status
  [[ -s "${status}" ]] && return 0
  tmpdir=$(mktemp -d /tmp/zpd-cw-javac.XXXXXX)
  if timeout 10s javac -proc:none -J-Xmx128m -encoding UTF-8 -d "${tmpdir}" "${source}" \
      >"${tmpdir}/stdout" 2>"${tmpdir}/stderr"; then
    rc=0
    compiles=true
  else
    rc=$?
    compiles=false
  fi
  printf '%s\t%s\t%s\n' "${id}" "${compiles}" "${rc}" > "${status}.tmp.${BASHPID}"
  mv "${status}.tmp.${BASHPID}" "${status}"
  rm -rf "${tmpdir}"
}
export -f compile_one

find "${SOURCE_DIR}" -maxdepth 1 -type f -name '*.java' -print0 \
  | xargs -0 -r -P "${WORKERS}" -I '{}' bash -c 'compile_one "$1" "$2"' _ '{}' "${STATUS_DIR}"

find "${STATUS_DIR}" -maxdepth 1 -type f -name '*.status' | wc -l
