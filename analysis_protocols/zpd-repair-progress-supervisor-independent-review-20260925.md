# Progress32 supervisor: independent lifecycle review

2026-09-25. Reviewer `repair_latest_diagnosis` did not author
`supervise_zpd_repair_progress.py`. Scope: the outside supervisor's resource,
process, stage-transition and final-seal behavior. Guard authorization,
numerical correctness and the scientific assessment have separate reviews;
dependency calls are not counted as independent reimplementation here.

Only source inspection and mocked/temporary synthetic lifecycle tests are
permitted and used. No child program, actual resource-limit setting, empirical
input, replay, source program, model, label, SSH or fit is executed/read by this
review. The resource setter is mocked, not applied to the reviewer process.

## Initial source review and raw findings

Root identified the following three terminal/ledger gaps during parallel source
review. This reviewer confirmed the relevant ordering in the initial draft and
sent them to the author; they are not claimed as independently discovered.

1. The last external barrier ran after the last `_files` check and immediately
   before return. A mutation during that callback could evade the file check.
2. The outer COMPLETE writer's returned hash was discarded; the exact bytes
   written were not compared after terminal consumers.
3. The manifest and next-action writer hashes were discarded. A later fresh
   hash could adopt changed content as the seal's expected content.

These are integrity-boundary findings, not evidence of actual corrupted output
or a changed scientific gate. Requested corrections preserve write-time hashes
for immutable outputs, check output files after the final external barrier,
and preserve/check the exact outer COMPLETE hash. Mutable stages/status/events
have a separate final-journal boundary; they are not treated as immutable from
their first intermediate update.

## Independently checked process boundary

New tests are in `tests/test_zpd_repair_progress_supervisor_review.py`. Initial
seven tests passed with subprocess/resource/process-group operations mocked.
They cover:

- Exactly10 prescribed stages,900s for metadata/finalize/assessment and3600s
  for each fold/audit,30s heartbeat,32GiB soft and hard RLIMIT_AS.
- New child session, all six fixed environment entries, unbuffered child log,
  explicit pre-exec limit callback and bounded waits.
- Nonzero exit, timeout and surviving descendants cannot produce a successful
  child receipt. Cleanup is called only with the exact Popen object; the
  cleanup primitive targets only its process-group ID, not a process search or
  a global kill command. Mock evidence does not establish real OS enforcement.
- Existing child output and a changed stage budget are refused before spawn;
  there is one Popen attempt and no retry loop.
- Fold command construction uses only
  `scripts.run_zpd_repair_progress_job --project ... --fold ...
  --expected-capsule-sha ...` with the initialized external own-job hash.
  No global guard CLI, release path, sibling contract, or global provenance
  map is passed to a fitting child.

## Corrections and independent full-lifecycle checks

The author retained the manifest and next-action write-time hashes and the
outer COMPLETE writer's returned hash. After the last external barrier, the
supervisor now rechecks its artifact pins and the exact written COMPLETE hash.
The three source-review findings are **resolved** without changing any stage,
timeout, fitting objective, method or scientific gate.

The reviewer reused the author's temporary full10-stage fixture construction,
not its test methods, for six new mutation tests. They independently check:

- Replacing manifest bytes immediately after its original write cannot become
  a newly accepted expected hash at terminal inventory construction.
- The same protection holds for next-action bytes.
- Mutating next-action during the **second post-COMPLETE recheck**, after the
  preceding file pass, is rejected by the final file pass. This specifically
  reaches the original last-callback gap rather than an earlier barrier.
- Replacing physically written COMPLETE bytes while returning its original
  writer hash is detected. Replaced bytes are preserved as REJECTED_COMPLETE;
  accepted COMPLETE is absent and FAILED is present.
- Changing a previously completed stage marker's bytes stops before the next
  fold, even if its JSON meaning is unchanged. Receipt authority is the external
  consumed byte hash, not rederived content or a fresh marker hash.
- An otherwise positive independent audit with only12 methods cannot satisfy
  the required320-recipient/30-model/13-method terminal boundary.

All **13 reviewer tests passed in4.021s**. The combined author-supervisor8 and
reviewer13 suite passed **21/21 in8.042s**. The author suite additionally covers
the complete negative-gate path, exact ten-stage sequence, late audit-label
drift, no-release/no-output behavior, prior-log drift and an actual COMPLETE
write followed by a synthetic durability exception. Those author test outcomes
were rerun by the reviewer but are not claimed as newly designed independent
tests.

The complete negative scientific gate remains a completed result with no
automatic retry, promotion or refit. A failure after provisional outer
completion quarantines that marker and prevents accepted completion. The
supervisor's last input/label checks occur only after the independent audit;
the fitting child commands retain their isolated own-job interface.

## Final pins and disposition

- Supervisor:
  `8918fcb1658ce13dd3b5892fcfe1664b1c719f0523161933b9663afaf96f4e62`.
- Author supervisor tests:
  `b5b1f6e7347e41679d75f7ee7cc7961ac4d45411ab73487d6f7ee95754d25c5e`.
- Independent reviewer tests:
  `aa012d8bc6b12f69538204dca922b910c1e9b9b77bc64b971b200d2b591d936b`.

**Scoped implementation-review PASS.** No unresolved concrete supervisor
blocker was found in this source. Real Linux enforcement, cleanup timing,
runtime provenance and the separately authorized production result remain
outside mocked-test evidence. Guard/schema and numerical-result reviews are
separate required boundaries; this review does not replace them.

This review supplies no fit authorization or empirical effectiveness claim.
