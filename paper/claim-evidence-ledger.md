# ICSE-SEET 2027 Claim–Evidence Ledger

Updated 2026-10-21 after the user changed the venue to ICSE-SEET Research Paper.
This supersedes earlier narrative amendments; the underlying results and frozen
protocols are unchanged. No post-deadline experiment was started for this rewrite.

## Central finding

Trajectory-derived target choice induces a coverage–locality tradeoff under
matched inputs. Authentic history has not demonstrated a reliable additional
repair benefit under its controls. The existing canonical-v5 implementation is
retained; current-only Answer-3Seed is a supported serving recommendation within
its evaluated historical stack, not the highest score for every split or baseline.

## Claim map

Analysis paths below are relative to
`outputs/split-90-10/canonical-v5/analysis/`.

| Claim | Manuscript | Evidence | Boundary |
|---|---|---|---|
| Current-only terminal triple repairs 718/997 Seen and 203/250 Unseen inputs. | Abstract, Introduction, RQ1 | `fse2027-current-only-deployment-ladder.json` | LSGen is higher on Seen; current-only Answer-9Choose3 is 205/250 on Unseen. No backend-independent dominance. |
| Matched Progress targets lose 19.2/11.2 RR points but preserve more source on joint repairs. | RQ2 | `fse2027-paired-target-control-corrected.json` | 7,389 train / 931 validation per arm; Progress may include accepted targets. Joint-success locality is conditional, not education. |
| Java direct matched-target training reproduces both directions. | RQ2 | `fse2027-paired-java-control.json` | 181 student-held-out inputs; 155 Answer versus 92 Progress successes, 90 joint repairs. Not a peer-control replication. |
| Matched peer replacement increases coverage by 4.3/6.0 points. | RQ2 | `fse2027-cross-user-target-control.json`, `fse2027-peer-distributions.json` | Effect of the entire matching/replacement rule, not isolated user-identity causality. |
| Candidate breadth contributes 15.1 points on fixed draws; adaptation also contributes. | RQ3 | `fse2027-result-bridge.json`, same-draw and base-model analyses referenced by that bridge | Expected uniform single draw versus identical three-draw union. Do not substitute the separate 20-draw stream's first-draw contrast. |
| Checkpoint and history benefits are not consistently supported under matched controls. | RQ3 | `fse2027-current-only-factorial-corrected.json`, bridge prompt/cross-fit/checkpoint results | Historical Transformers and vLLM are separate stacks; non-significance is not equivalence. |
| Prefix, difficulty, hidden-slice, smaller-model and Java tests constrain generality. | RQ4 | Bridge all-prefix, difficulty, hidden, scale, exercise, verdict-order and overlap families | Eventually successful trajectories, one model family, four held-out Java exercises; hidden slices share an authored suite. |
| No new history-specific candidate meets every adoption condition. | RQ5 | `analysis_protocols/zpd-final-methodology-report-20261021.ko.md`, `analysis_protocols/zpd-deadline-results-20261021.json` (repo-relative) | Adaptive diagnostic runs, not independent confirmation. All original C/H/HS/U, regression, unknown, and fold rules remain. |
| Public execution improves a generic eight-draw-bank selector (252/320; 9 regressions; 13 unknowns). | RQ5 | `analysis_protocols/zpd-public-candidate-selection-result-20261012.json` (repo-relative) | H is 251/320; extra execution cost; bank contains initially accepted inputs and is not canonical failed-input RR. |
| Final preference training is complete but repair evaluation is absent. | RQ5 | `archive/zpd-preference-training-20261020/REPORT.json`, final deadline report (repo-relative) | 19,199 train / 4,365 validation per C/H arm. No RR, no promotion, no post-cutoff restart. |

## Implementation corrections reflected in the final text

- Answer uses independent single-source-to-accepted pairs, not accumulated history.
- Strict/Progress scan against the last retained state, include an accepted endpoint,
  and have independently constructed edge sets; those sets need not be nested.
- The primary mixed triple is the unconstrained Answer2027/Answer2028/Progress2027
  selection, not a forced one-of-each-relation portfolio.
- Runtime eligibility is current non-AC plus replay-accepted endpoint.
- The fixed execution gate guarantees only nondecreasing measured pass fraction;
  it does not guarantee per-test non-regression or stability under fresh execution.
- Python whitespace corrections remain in the reported outcomes; originals are preserved.
- No theorem, artifact seal, smaller patch, or predictive loss is presented as
  evidence of learning, educational efficacy, or scientific acceptance.

## Manuscript validation and publication limits

`main.tex` contains literal values and no user-defined `newcommand`.
`main.evidence-bindings.json` checks 27 literal snippets / 108 evidence-derived
values against the retained bridge. The historical bridge filenames remain
unchanged for provenance; they do not designate the current submission venue.

`scripts/verify_icse_seet_pdf.py` checks the exact IEEEtran class, 24pt title,
10pt body sample, anonymous metadata, embedded fonts, and 10 body + 2 reference
page limits. References deliberately start on a fresh page. Full rendered-page
inspection is recorded in the rewrite status report and is distinct from an
independent scientific review.

No anonymous artifact deposit, submission, public push, new experiment, or
independent paper review was performed in this writing turn. The older Korean
translation is preserved but is not the synchronized final manuscript.
