# Progress32 readiness implementation: independent review

2026-09-25 (KST). **PASS for the pure readiness implementation only.** This
review does not authorize replay, empirical feature loading or fitting, and it
does not establish repair improvement. No empirical source, prepared sample,
replay, candidate-bank or repair-label body was read. No SSH, execution unit or
fit was used.

## Scope and independence

The reviewer did not author or modify `zpd_statement_sample_readiness.py`, its
tests, or the progress32 encoder. The reviewer previously authored the
prospective design document; consequently this is an independent **implementation
compliance** review, not an independent review of that design's authorship or
scientific hypothesis. The complete prospective document was read, including
the sixth conjunctive readiness condition.

Reviewed pins:

- Protocol `zpd-statement-sample-progress-prospective-20260924.md`:
  `e53334b68c2d54b430931d8369ad3ca86946ad457f79644ba9a304460ad9348f`.
- `scripts/zpd_statement_sample_readiness.py`:
  `b938b700623844e36d0154ea511bb232c0f5074ac8921e07dccd62a982e2cb9c`.
- `tests/test_zpd_statement_sample_readiness.py`:
  `237bd0df12fe94447d522f7d11bc231c4a36b7cd9c4720dc48e9cd6ca1314117`.

## Findings and resolutions

The initial draft accepted candidate-dependent current counts and source/history
facts, did not require literal-zero moment arrays at zero opportunity, and did
not require one common declared sample count per problem. These could make
malformed supplied records look like candidate-aligned variation. The author
added the checks and mutation regressions before this review's final run:

- Current counts, source-feedback reasons, historical delta masses and supplied
  permutations agree across candidates; parsed candidates share historical
  eligibility and paired counts.
- Candidate availability/mass agree across arm scopes. Zero opportunity has
  literal-zero moments; unavailable candidates and unknown current feedback
  cannot expose nonzero model coordinates.
- All recipients of one problem share its declared full sample count.

These were input-contract corrections, not changes to controls, weights,
thresholds, cohort membership or the six scientific feasibility requirements.
No unresolved implementation blocker was found in this bounded review.

## Contracts checked

The implementation retains 320 unique users/examples/banks, 23 problems and
2,544 candidates, with all five nonempty problem-held folds and exact feature
map coverage. It evaluates each training complement, not the corresponding
held fold or a four-of-five readiness vote. All six requirements (nine Boolean
checks because condition3 has four controls) are conjunctive in every training
fold. Missing feedback and empty sample universes remain explicit zero-feature
records, not inferred failures or excluded examples.

Conditions1/2/4/6 require two non-noop edited candidates. Condition3 correctly
allows any pair and also reports edited-only geometry. Condition2 uses exact
equality of the old18 values multiplied by their Boolean masks. All geometric
decisions use strict `> 1e-12` on final scaled coordinates; equality does not
pass. A common edited offset distinguishable only from no-op cannot satisfy
the edited-pair requirements.

Condition6 is independently reconstructed from the original H conditional
weights and eligible nominal WA-to-WA paired counts, retaining only states01
and10. It uses the original transition positions and the single sqrt12 scale,
without renormalizing the WA subset. A progress witness unrelated to candidate
variation cannot rescue this condition. The report always returns
`fit_release_authorized=False`, even when its pure readiness decision is true.

## Synthetic verification

Command independently rerun:

```text
.venv/bin/python -m unittest tests.test_zpd_statement_sample_readiness tests.test_zpd_statement_sample_progress -v
```

Result: **28/28 PASS, 1.862 seconds** (12 readiness and16 encoder regressions).
The denominator witness with eligibility `[true,false,false,true]` retains
first-transition weights1/2 and1/5, rather than subset renormalization or
compacted recency. Boundary and mutation tests cover strict tau, masked-event
ties, held-only support, each required predicate, unavailable records, source
fact consistency and full cohort/candidate coverage.

A separate ephemeral scalar check used fixed seed250925 and40 synthetic banks
with history lengths0/1/2/5/14, one to four declared cases, missing feedback,
unparseable candidates and no-op. All200 candidate contribution vectors agreed
exactly with independently constructed positional weights and scalar fsum.
Independently enumerated all/edited pairs agreed with every arm's variation and
all five H-control contrasts. No corpus files were opened for this check.

## Remaining authority boundary

This pure module accepts precomputed encoder moments. It verifies their listed
structural invariants and independently recomputes condition6; it is not a
replacement for authenticating source/suite/runtime identities, original bank
seals, donor membership, exact fold identities or replay completion. It also
does not independently reconstruct every supplied32 feature from source. The
caller must bind and validate those inputs using the frozen encoder and sealed
provenance chain. Real readiness remains unmeasured by this review; passing it
would still require a separate fit release and would not predict a repair gain.
