# Repair-feedback source-only support preflight

Implementation only, pending independent review and clean-snapshot release.
No real support audit, fitting, candidate execution or new outcome collection
was performed during implementation. Fifteen synthetic tests pass locally.

The inventory found all required original64/train256 preparation manifests,
observations and requests; original generation and four expansion generation
chunks; merged expansion banks; original observed source-language manifest and
prepared metadata; and sealed structure-CV fold metadata. The actual generator,
prompt-builder and extractor source hashes agree with their generation manifests.
No missing required file was replaced by an assumption.

`scripts/audit_zpd_repair_feedback_support.py` exposes:

- `load_inputs(project, production=True)`: an explicit source-only filename
  allowlist; returns observations, typed banks, frozen fold assignment,
  source-language coverage and a recheckable input reader. The production CLI
  has no option to weaken its pinned parent/prepared checks.
- `join_observations(...)`: pure exact recipient/donor metadata, source SHA and
  original-language join; requires the full selected bank/fold identity set.
- `interaction_matrices(observation, bank)`: all candidates' 18 values/masks and
  H/Jm/HS/L/U 1296-coordinate matrices; no source execution or outcome access.
  The optional `with_history_support=True` adds bank/arm-specific observed
  applicability counts, positive-event counts, mask-conditioned distinct nominal
  verdict-pair counts and uniform/recency opportunities. Zero opportunity,
  single opportunity, observed event zero, constant event and constant feedback
  are separate flags, also aggregated by arm/event/fold. A missing event is not
  relabeled zero and feedback constancy uses the same applicability mask.
- `support_summary(...)`: source-only full-bank/fold support with every candidate,
  raw event masks, exact signature-equivalence groups, effective masked-event
  groups, all unordered pair counts and **pairwise** covariance contrast counts.
  Separate edited-only interaction classes and pair counts expose whether the
  residual can distinguish two repairs, rather than merely edit versus no-op.

The contrast is `(phi_H(a)-phi_H(b))-(phi_control(a)-phi_control(b))`, not simply
whether historical moments differ. The report directly calculates maxima and
counts over every unordered pair and retains no-op-anchored maxima separately.
For the actual binary candidate-gate times bank-shared moment construction these
maxima agree; the diagnostic does not assume that identity for arbitrary supplied
matrices. A synthetic near-tolerance case tests its general all-pair definition.
The fixed tolerance is `1e-12` in scaled interaction coordinates; it is descriptive
and never filters rows or candidates. Same-signature groups expose the inability
of an interaction-only residual to change the base ranking inside those groups.

Generation provenance establishes the **declared Python repair contract**, not
successful parsing or proof that the generated text is Python. The pinned generator
builds language-unspecified records, the pinned builder defaults that record to
Python, and the pinned extractor is `extract_python_code`. Candidate parse errors
remain represented with the frozen event applicability masks. Actual historical
source language comes only from the exact original path/identity/SHA join.
UTF-8 decoding is strict and roundtrip checked; no replacement or normalization.

The original physical preparation/generation files include valid32 source-only
rows. Their shared source artifacts are verified, but only the fixed train64
rows enter support, alongside train256. Neither evaluator/fit loaders nor any
evaluation, label, model, prediction or successor file is opened. Parent manifests
contain other file hashes as metadata; the reader never follows those paths.
Donors remain the old external same-problem observed donors, not a newly sampled
problem-fold-training donor population. No donor current or future code is used.

Prospective command after independent review, from a clean committed source
snapshot with the canonical project data root:

```
python -m scripts.audit_zpd_repair_feedback_support \
  --project /home/cdw/VSCode/zpd-apr \
  --output /home/cdw/VSCode/zpd-apr/outputs/zpd-repair-feedback-20260924/support-v1
```

The CLI rejects existing outputs, aliases/symlinks and a dirty source snapshot.
It writes only a new direct child of the named family, records source/runtime/
input seals (including this preflight and the prospective contract), retains a
failure marker on preflight errors after output creation,
and rechecks all consumed inputs plus source state immediately before COMPLETE.
The report always says `fit_release_authorized=false`; geometric support is not
a correctness result or an automatic fitting release.
