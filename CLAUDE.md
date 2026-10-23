# CLAUDE.md (dev)

ZPDPatch: the technique, its experiment runners, and the results the evaluation reports. Repository, branch, and
artifact rules follow the project template (`main` = this branch minus `tests/`, `CLAUDE.md`, `AGENTS.md` and internal
safety devices).

## Experiment deadline (2026-10-21)

The user limited ZPD-APR improvement experiments to **2026-10-21 13:00 KST**
(`analysis_protocols/zpd-deadline-20261021.json`). Do not launch, retry, or resume experiments after that time unless a
newer explicit user instruction extends it; `analysis_protocols/zpd-deadline-extension-20261023.json` is the one
extension so far (family `histra-bench-20261023-v1` only). Do not alter the active frozen release, datasets, gate, or
reporting denominator. Preserve interrupted runs' files, mark them incomplete, and never manufacture a normal-exit or
COMPLETE certificate. Analysis and verification of saved results remain authorized. No claim of educational or
confirmatory benefit. Existing experiment source snapshots (tags `snapshot/*`, server `.runtime/*/source`) stay
unchanged; register any new family with its own protocol and the deadline policy.

## Running

- Heavy runs go to UbuntuServer, one workspace at `/home/cdw/VSCode/zpd-apr` (no sibling checkout). GPU jobs use
  `.runtime/fse-env/bin/python` (`env/` there no longer holds torch), run as `systemd-run --user` units from a source
  snapshot under `.runtime/<family>/source`, and never share the machine with another CPU-heavy job while tests run.
- Copy finished results back to the local results folder and check them against their manifest before using them.
- Tests: `PYTHONPATH=. TMPDIR=/private/tmp env/bin/python -m unittest discover -s tests -q` (unittest, not pytest).
