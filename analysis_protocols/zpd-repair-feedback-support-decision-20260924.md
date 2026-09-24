# Repair feedback: observed-only support completion

The source-only320-bank audit ran on UbuntuServer at19:55 KST and completed
before19:56:17. It did not fit, execute a candidate or read an outcome, successor,
learned model or prediction. This is feasibility evidence, not a repair result.

## Execution and evidence

- Dev source:`effd0bf68ae72e3193e4d9f5ee3fbefb4d531c56`.
- Exact tree:`1313e6cc24bf9d1f54ca3f1a17f4e4029c402951`.
- Parentless execution snapshot:`dd6bc981f552de193f80eb68a05a4247a18f9798`.
- Local source:`/private/tmp/zpd-repair-feedback-source.U7eKC6`.
- Remote source:`.runtime/repair-feedback-support-20260924-v1` under the
  canonical `/home/cdw/VSCode/zpd-apr` project; its main checkout was not changed.
- Bundle:`.runtime/zpd-repair-feedback-support-20260924-v1.bundle`, SHA256
  `a0b93d386c6ea74efeec7c79dbe04aa2360692c75b57108c173790920f0b76c2`.
- Both exact-tree local and server suites passed495 ZPD plus19 pilot tests.
  Synthetic failure-injection logs and existing scaler warnings were retained;
  no failing test was suppressed. The clean source was rechecked before launch.
- tmux:`zpd-repair-feedback-support-20260924`, launched19:55:53, terminated
  naturally upon completion. The independent C3 session was left running.
- The launch used one BLAS thread,32GiB limit and30-minute INT timeout, running
  `scripts.audit_zpd_repair_feedback_support --project` with the canonical root
  and a new `outputs/zpd-repair-feedback-20260924/support-v1` output directory.

The completed output was copied without overwriting an existing local result.
All four sealed output hashes and all36 input/16 source hashes were verified on
the server, and the output seal was verified again after synchronization.

- COMPLETE:`64d8f2a11de01ee08a2ed0ac51ac44b1ad4ec56281eaac971eadbb88cc4270d0`.
- Report:`afb6d1782811e8c6edf962077bd809c1a8cee3370936e6e3619cfb20861f82a3`.
- Manifest:`7904c6fa8150170b74eab6efcbe906db5de2ae5ada326d1f4ca7c6589c216bae`.
- Folds:`07258b61d8b3eae16370afa43e8fd94299bc72507b3d81de215aaa5bc50b5592`.
- STATUS:`705aa90b59bc1b8d9e4ffe50dc026d395bdbbc7659913cfcc5837452d1c16ed3`.

## Results, without sample or gate changes

All320 recipients/users/banks across23 problems remain, with2,544 deduplicated
candidates and9,231 unordered candidate pairs. No prefix was excluded. All
eight terminal attempts per original bank remain verified, including failures.
The original-language exact join covers1,611 distinct observed source IDs:
Python1,581, C++19, C3, PHP3, Ruby2, C#1, Java1 and Swift1. All current sources
are certified Python; non-Python historical sources retain their event masks.

| Source-only quantity | H | Jm | HS | L | U |
|---|---:|---:|---:|---:|---:|
| Banks with within-bank interaction variation |310|310|310|305|308|
| Banks with multiple edited-candidate interaction classes |222|222|222|183|269|
| Banks with pairwise H/control contrast | — |58|94|163|295|
| All varying candidate pairs |5034|5034|5039|4345|6124|

H/Jm has914 distinct candidate-pair contrasts, including549 edited-only pairs
across44 banks. H/HS has1,601 contrasts, including962 edited-only pairs across71
banks. Thus the residual is not universally restricted to edit-versus-no-op
switches. This does not establish that any newly reachable candidate is correct.

All144 prior-one cases remain; they have identical H/Jm features by construction.
In total262/320 banks have no H/Jm candidate-pair contrast and remain in every
applicable fit/assessment. Independently fitted arms can still differ there
through learned coefficients; the fixed shared-theta diagnostics address that
distinction without selecting a favorable subset.

Held fold sizes remain66/65/62/62/65. Every training fold has245–252 varying H
banks and40–50 H/Jm-distinct banks. Held H/Jm counts are10/12/8/10/18. The fixed
geometric variation prerequisite passes. Root independently recounted the
population and all10 train/held aggregates, checked all row/fold identities,
pair maxima/count consistency, prior-one equality and identical H/Jm historical
applicability diagnostics. The prior independent source review remains separate.

## Decision

Continue preparation of the predeclared fixed-base repair residual; do not
change its representation, population, controls or thresholds. The support
artifact deliberately keeps `fit_release_authorized=false`. Actual fitting
still requires the exact fold-local label provider, pure pair/scoring module,
optimizer, executable assessment gate, independent implementation review and
a separately committed execution release. No C3 weights may enter repair.

The actual correctness, anti-abstention, preservation and mechanism gates are
unchanged. A C3 proxy pass or this support pass cannot substitute for them.
