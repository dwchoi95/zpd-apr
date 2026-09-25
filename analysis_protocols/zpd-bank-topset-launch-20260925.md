# Bank-topset comparison: native pretest and one-shot launch

2026-09-25 11:21 KST. Authorized autonomous development comparison; no paper
claim or model promotion. The previous joint4131 negative run is unchanged.

## Preconditions and preserved failure

The own-training diagnosis was independently verified: 1,280 repeated training
incidences, 203 known-AC misses and 40/67 OOF misses also missed in all four
training roles. Pair-gradient conflict is observational, not a causal result.
The prospective objective, plan, native solver, own-worker/coordinator and
final-point auditor received bounded nonauthor reviews. Findings and corrections
remain in their raw review documents. No threshold or population was changed.

Initial minimal snapshot v1 had 227 files and failed its Linux import pretest
before any empirical or synthetic model fit: package initializer dependency
`src.repair.compare` was absent. Fourteen pure-objective tests passed; seven
test modules failed import. Snapshot retained at
`.runtime/topset-release-20260925-v1/source`, revision
`6338139ec2f25f929c4d27c492affbbda401a188`, tree
`8c1c645c1de1f4420c3e6e03b4cb0968ed16691f`.
Its archive SHA is `446d60b0c59025baca2c5fa87261d70af78cd11967ec135779473486ccfc218a`.
No empirical release or fit had occurred, so this was not an experiment retry.

The reviewed correction binds all existing src package dependencies and the
missing synthetic fixture, and rejects loaded local modules outside the declared
closure. No scientific code, objective or control was changed by that correction.

## Accepted source and Linux pretest

- Dev source commit: `35cb21fb` (implementation `09975d32`).
- Clean execution root:
  `/home/cdw/VSCode/zpd-apr/.runtime/topset-release-20260925-v2/source`.
- Execution revision: `b8edcfa83d081f1a48f57c60138a167f431e5889`.
- Tree: `fe4ea7ce7063d52dfe1c55353df625d5b398e45e`.
- Source archive SHA:
  `12e7f528c2a240baa9d3361ef58001288e0c563731a81280a8df49a15aeff3e8`.
- All 246 exported files matched committed dev HEAD exactly. Existing dirty
  user files, including src/repair/evaluate.py and the paper, were not exported
  from their worktree versions and were not edited by this work.
- Python 3.13.11, NumPy 2.5.2, SciPy 1.18.1, scikit-learn 1.9.0, tqdm 4.70.0;
  fixed five single-thread variables plus JE_ARROW_MALLOC_CONF=background_thread:false.
- Linux soft/hard RLIMIT_AS=32 GiB set before test imports.
- `unittest discover -s tests -p test_zpd_bank_topset*.py -v`:
  **68/68 PASS, 44.734 seconds**. Includes a real seven-arm synthetic own-fold
  fit (27.159 seconds) plus native4131 scalar-reference tests. No empirical data
  fit was part of this pretest. Test artifacts stayed beneath the canonical
  project runtime TMPDIR, outside the clean source snapshot.
- Captured log: `archive/zpd-bank-topset-release-20260925/linux-pretest-v2.log`,
  SHA `36eed425d05c199d612d30479c9283c80e4e9898de78e2a01d9170289b500d33`.

## New run and monitoring contract

New release JSON SHA:
`282ffea113d1744233a16fd2cdceb23341b6b875fe2ce27292bf7659be0598b1`.
Its 246 source pins, Git identity, protocol, full runtime and native identity
are bound separately from the old source-capsule authority.
Server output: `outputs/zpd-bank-topset-20260925`; tmux session
`zpd-topset-20260925`, launched 11:21:05 KST. At 11:21:28 supervisor PID2052153
and fold-0 child PID2052169 were live, no FAILED marker. These are observations,
not permanent process identities; recheck before any later operation.

Five one-shot children fit seven same-objective arms each. Fixed folds cover
all320/23 problems/2544 candidates. After all predictions are sealed, the same
fourteen-method assessment and all four scientific gates run unchanged. A sixth
bounded child checks all35 new final gradients independently with direct affine
contrasts and replays held predictions. No retry, new candidate execution,
full-train refit, threshold relaxation or automatic promotion is authorized.
Every child has the existing 3,600-second watchdog and 32-GiB address-space cap.

Report progress as completed held examples /320, distinguishing repeated
training-example/model incidences. First-fold timing is needed for a useful ETA;
no completion-time guarantee was made. Normal gate failure is a completed
negative result; numerical/resource/provenance failure stops the pipeline.
The root will inspect the verified result before choosing a next intervention.
Codex goal state remained usageLimited at launch despite working tools/agents;
no hourly Scheduled reservation or restored automatic goal continuation is claimed.
