#!/usr/bin/env bash
set -euo pipefail

SOURCE_ROOT=${1:?source directory required}
STATUS_ROOT=${2:?status directory required}
mkdir -p "${STATUS_ROOT}"

compile_one() {
  source=$1
  slug=$(basename "${source}" .java)
  work=/tmp/zpd-codeworkout-"${slug}"
  mkdir -p "${work}"
  cp "${source}" "${work}/Main.java"
  if timeout 15 javac -encoding UTF-8 "${work}/Main.java" >"${work}/compile.out" 2>&1; then
    if timeout 15 java -cp "${work}" Main >"${work}/run.out" 2>&1; then
      status=ok
    else
      status=runtime-error
    fi
  else
    status=compile-error
  fi
  {
    printf '%s\n' "${status}"
    if [[ -f "${work}/run.out" ]]; then
      cat "${work}/run.out"
    else
      cat "${work}/compile.out"
    fi
  } >"${STATUS_ROOT}/${slug}.txt"
  rm -rf "${work}"
}
export -f compile_one
export STATUS_ROOT
find "${SOURCE_ROOT}" -type f -name '*.java' -print0 \
  | xargs -0 -n 1 -P "${ZPD_JAVA_WORKERS:-32}" bash -c 'compile_one "$1"' _
