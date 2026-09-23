# Full-history action compatibility: implementation-ready design

Status: design and train-only schema/coverage audit, not implementation approval
for a new outcome run. No model is trained, no source is executed, and no
validation/test outcome file is opened in this work. This stage is independent
of the ordered-structure cross-validation results. Frozen repair results and
their correctness/non-regression gates remain unchanged.

## 1. What this stage can and cannot test

The concrete hypothesis is: authentic full submission history improves prediction
of the author's **immediate next observed edit**, beyond current code, attempt
count, unrelated matched history and shuffled authentic history. The target is
an observed action, not eventual AC and not the best future submission.

An action-likelihood model can supply a candidate-by-history compatibility score.
It does not establish that the action is good instruction, within the author's
ZPD, causally caused by a scaffold, or improves retention/transfer. Actual next
submissions may be wrong, regress, repeat code, copy a solution or follow outside
help. CodeNet does not observe instruction or learner state. Behavioral prediction
must remain separate from repair correctness and educational effectiveness.

There must be no target rule such as "next improved submission", "first future
AC", "smallest successful future patch", or "next Python after a language
switch". Those rules reintroduce future selection and erase failed actions.

## 2. Existing sources and exact boundaries

| Source/API | Available fields and use | Restriction |
| --- | --- | --- |
| `scripts/build_zpd_original_prefixes.py:build` | Original CodeNet metadata grouped by user/problem; full ordered `observed_history`; immediate `next_submission` metadata | Existing builder emits all splits and intentionally does not read sources after the last non-AC current. Do not rerun it as a target collector. |
| `outputs/zpd-history-gate-20260915/original-prefixes/{manifest,features,references,codes}.json[l]` | Original-language information, strict-prefix provenance and exact-byte source hashes | `labels.jsonl` combines splits and remains closed. Scope is the release snapshot, not lifetime history. |
| `scripts/run_zpd_history_gate.py:prepare/load_training` | Split-sealed preparation; `features.jsonl` with `example_id,user_id,problem_id,split,timestamp,current_code_id,current_verdict,matching_current_verdict,history,donor_example_id` | `labels-train.jsonl` contains only `example_id,next_label`; it does not contain next code/ID/time. Do not call `prepare` to recover target code: it opens combined labels. |
| Prepared `history[]` | `code_id,verdict,timestamp`, all strictly prior submissions | Language is dropped here; recover it from original observed-prefix metadata, not by assuming every prior submission is Python. |
| `src/repair/pilot_contracts.py:ObservationSource/PilotObservation` | Exact source bytes, source SHA, nominal verdict and strictly increasing timestamps | IDs and timestamps validate provenance; IDs are not learned features. |
| `src/repair/pilot_ranker.py:features` | Full-history edit/reverse-edit overlap and exact reversion | Current implementation is token-order lossy and does not use verdicts as learned features. A new encoder must be separately versioned. |
| `src/repair/zpd_state.py:build_observed_prefix_state` | Nominal transitions, repetitions, optional testcase new/lost passes and persistent failures | It permits timestamp ties; the new preparation must enforce strict order externally. Its testcase input requires external stability/provenance certification. |
| `scripts/audit_zpd_history_support.py:match_donors` | Exact problem/raw-verdict/prior-count/prior-token matching; different, strictly earlier training user; optional fold-training user restriction | Rebuild donors within every training fold. Existing donor IDs are not automatically valid for cross-validation. |
| `scripts/zpd_repair_structure.py:structure_counts` | Source-only ordered AST field/adjacency signatures with byte fallback | Reuse only via a pinned hash/version; it is not a semantic edit aligner or learner model. |

The original manifest records the read-only release locations:

```text
/Users/cdw/VSCode/aria/data/Project_CodeNet/metadata/<problem_id>.csv
/Users/cdw/VSCode/aria/data/Project_CodeNet/data/<problem_id>/<language>/<submission_id>.<filename_ext>
```

These are observed paths in the existing manifest, not newly searched directories.
Canonical-root copies may supply already available source bytes:

```text
outputs/zpd-history-gate-20260915/prepared-inputs/codes.jsonl
outputs/zpd-history-gate-20260915/original-prefixes/codes.jsonl
data/<problem_id>/submissions/<user_id>.jsonl
archive/legacy-20260711/data/<problem_id>/submissions.jsonl
```

The last two are optional derived inventories, not proof of full raw coverage.
Do not replace the original cohort with their eventual-AC-filtered trajectories,
skip missing intermediate submissions, or normalize whitespace. Accept a derived
copy only after exact `(problem,submission)` metadata join and equality to an
already certified raw source SHA; otherwise recover the raw file or mark source
provenance unavailable. The original manifest does not certify terminal source
files that the old builder deliberately did not read.

On UbuntuServer all new target inventories, logs and copied target bytes must
remain under `/home/cdw/VSCode/zpd-apr/`. Do not create `/home/cdw/zpd-apr` or
new top-level home artifacts. No canonical-root full CodeNet release location
has been verified in this task; do not invent one. If needed, prepare locally
from the documented read-only release, then synchronize only the sealed
train-only inventory into the canonical server root.

## 3. Verified training-only source-availability blocker

This audit read the existing prepared manifest/features and `labels-train.jsonl`
only. It did not open `labels-valid.jsonl`, `labels-test.jsonl`, original combined
labels, or any new execution outcomes.

Manifest SHA:
`4fd3e23b0157bd09cff232131fdcfa5134f335239f59ffd7039f5392d398a60d`.
Feature SHA:
`db0b8ab67d905d44b9dc095441bb225822154c858eb61886640f5dcd6ceb244c`.
Training-label SHA:
`ee30e1527da44eb691eaec2526e03b4cd5fe687091527d76461f857cf7d241bc`.

Consecutive entries in later full **training** prefixes recover some earlier
prefixes' immediate successor. There are zero conflicting successor joins and
zero disagreements between their observed next nominal verdict and the sealed
training label. This is only availability diagnosis, not a substitute target
corpus.

| Existing train cohort | Prefixes | Users | Next source exposed in a later train prefix | Not exposed | Next-AC among exposed / not exposed |
| --- | --- | --- | --- | --- | --- |
| All training, 23 problems | 71,191 | 8,473 | 47,142 | 24,049 | 1,450 / 19,484 |
| Existing exact-donor-matched training | 31,980 | 7,102 | 20,856 | 11,124 | 534 / 9,158 |

Recovered-source users number 6,637 and 5,570, respectively. Source recovery
from later prefixes heavily excludes terminal/last successors, including many
ACs. Training only on this convenient subset would create strong outcome-related
selection even if the source lookup itself never inspected verdicts. It must
not silently become the primary training population.

## 4. Minimal next preparation implementation

Implementation update: the narrower C0 source-recovery stage is now implemented
as `scripts/prepare_zpd_train_successors.py` under
`zpd-train-successor-recovery-20260923.md`. It leaves the existing observation
artifacts untouched and produces a separate target-only file. It does not yet
implement the full feature/target event encoding package described below.
See `zpd-method-autonomous-status-20260923.md` for the actual completed command
inputs, source revision and target availability; the following larger-package
API/command remains a design specification, not an executed learner.

Proposed new module, **not yet present**:
`scripts/prepare_zpd_history_action_targets.py`.
Proposed public entry point:

```python
prepare_train_targets(
    prepared_root, original_prefix_root, metadata_root, raw_data_root,
    canonical_repo_root, output,
)
```

Its bounded contract is to resolve exactly the existing 71,191 training prefix
IDs on the existing 23-problem roster. It does not expand the cohort, refit a
split, train a model, execute code, or open any held-out label file.

1. Verify existing preparation/source/support manifests. Obtain the train-user
   and train-example allowlists from `features.jsonl` with `split == train`.
   Input-reader tests must reject accesses to labels-valid/test and combined
   labels. Retain all earlier source entries and exact repeat submissions.
2. For the 23 already recorded metadata CSVs, verify recorded whole-file hashes.
   A metadata reader must filter to allowed training users before accessing or
   retaining status/language/successor fields; never derive held-out outcomes or
   counts. Reconstruct full same-user/problem order from original metadata.
   Match each current ID/time/raw verdict to its frozen prefix. Ambiguous order,
   a missing metadata row or any prefix mismatch fails closed with an audit row.
3. Resolve the actual immediate successor by metadata adjacency, **not** by
   searching forward for a readable/Python/accepted source. Verify strict
   `t_next > t_current`, user/problem identity and the original next-category
   training label. Missing/tied/censored cases remain explicit, never zero-edit.
4. Search the allowlisted canonical code stores first for this exact target ID;
   use only exact-byte, certified raw hashes. Otherwise read its safe raw-release
   path using the metadata `language` and `filename_ext`; record new source SHA,
   raw path and copied bytes in the target-only store. Missing/undecodable source,
   language switch and parse failure are different statuses. No source execution.
5. Write physically separate immutable files:
   `observations-train.jsonl`, `observed-codes.jsonl`,
   `targets-train.jsonl`, `target-codes.jsonl`, `coverage.json`,
   `exclusions.jsonl`, `manifest.json`, `COMPLETE.json`.
   Each observation has only current/prior byte references, nominal verdicts,
   languages and strict timestamps. Each target has `example_id,next_code_id,
   next_source_sha256,next_timestamp,next_language,next_nominal_verdict,
   source_status,target_status`. No target field enters the observation schema.
6. Retain every input prefix in the coverage denominator. Report missing source,
   language switch, order mismatch, raw-copy mismatch, Python parse failures,
   duplicates, exact no-op, donor availability and prefix length by problem and
   training next-verdict. Never drop all repeated or unsuccessful transitions.
7. Seal script/protocol/runtime/input/output hashes and exact allowed target IDs.
   The target source loader must be inaccessible to the feature encoder. A test
   that mutates all target codes/timestamps/verdicts must leave observation
   features byte-for-byte unchanged. Modifying one training user's target must
   not alter another user's donor selection or feature representation.

Proposed command after the module, tests and protocol are independently audited:

```sh
python3 -m scripts.prepare_zpd_history_action_targets \
  --prepared-root outputs/zpd-history-gate-20260915/prepared-inputs \
  --original-prefix-root outputs/zpd-history-gate-20260915/original-prefixes \
  --metadata-root /Users/cdw/VSCode/aria/data/Project_CodeNet/metadata \
  --raw-data-root /Users/cdw/VSCode/aria/data/Project_CodeNet/data \
  --canonical-repo-root /Users/cdw/VSCode/zpd-apr \
  --output outputs/zpd-history-action-20260923/prepared-train-v1
```

This command is a handoff specification, **not an executable command today**.
Prerequisites: verified readable raw metadata/source roots or certified canonical
copies, a clean committed implementation snapshot, synthetic leakage/coverage
tests, a pinned preparation protocol and a new output directory. Incomplete raw
source availability blocks primary target completion; it does not justify using
the biased convenient subset or opening another split. Preparation completion
does not automatically authorize training or hidden-test access.

## 5. Full-history state and candidate interactions

For current `s_t`, retain every observed `s_1 ... s_(t-1)` and every adjacent
transition through `s_t`; no maximum-history option, subsampling, deduplication
or first-AC truncation. A bounded feature vector may aggregate all transitions;
the retained raw sequence and contribution count prove none were discarded.

State components:

- Nominal verdict frequencies/transitions, repeated-current-verdict count and
  last verdict. Repeated WA means repeated **nominal verdict**, not the same bug.
- Exact-byte recurrence count, trailing repeat run, most recent exact return to
  a previous source, and recurrence distance. Source SHA is a join/comparison
  key only, never a hashed identity feature.
- Directional AST/ordered-token edit signatures for every adjacent transition:
  addition/removal, operation family, changed parent field, and statement/list
  ordering. Store reciprocal-recency weighted sums and unweighted recurrence
  counts with full denominators. Preserve parser/language-fallback indicators.
- Repeated edit/reverse-edit patterns and whether a candidate restores previously
  removed structure, repeats an attempted edit, reverses the latest transition,
  or exactly returns to a past source. These are observations, not frustration,
  understanding, readiness or mastery labels.
- "Resolved" is initially restricted to a demonstrable static event such as
  parse failure becoming parse success, or a historical judge category changing
  to AC. WA→RE is not intrinsically an improvement. Testcase resolution is unknown
  unless both prefix endpoints have stable evidence under an identical sealed
  test universe/runtime. Existing v5 `outcome_cache_complete=true` alone is not
  a four-block stability certificate; the repair bank evidence does not cover
  every past source. Do not fill missing prior testcase outcomes with zeros.

For candidate patch `p`, let `d_t(p)` be its direction-sensitive edit signature
relative to current, and let `r_t` be the full-history state. Include candidate
interactions explicitly: `d_t(p) × recurrence/reversion/resolution indicators`,
overlap with prior forward/reverse edits and exact-source recurrence. A constant
history feature added equally to every candidate cannot change within-bank
ranking, even when it predicts overall difficulty well.

## 6. A next-action objective, not another AC label

First implement a target encoder shared by training targets and candidate
patches: `encode_edit(current_bytes, next_or_candidate_bytes, languages)`.
The label is a multi-label immediate-edit signature, with fixed versioned event
families: exact repeat; token-equivalent surface change; parse recovery/loss;
arithmetic, comparison, Boolean, branch, loop, binding, call, indexing/container,
function/return, exception and import edits; ordered AST relation change; and
other lexical change. Node/operator-family mappings and parser version must be
enumerated in code and sealed before fitting. Order changes cannot be inferred
only from unordered AST node counts. "Other" preserves changes outside the
taxonomy; it is not silently discarded.

Language switch is a separate observed target flag. Python-AST family labels
are masked unavailable when either endpoint is another language or unparseable;
they are not set to "no edit". Exact-byte/token/fallback and language/parse
events retain their own applicable denominators. Source missingness is a
coverage condition, not a predicted desirable action. Report all event masks.

A bounded first learner predicts these event probabilities from current plus
state using a fixed linear logistic head per event. The primary loss is
user-equal, observed-event masked binary negative log likelihood; per-event
denominators and losses must also be reported so syntax/source availability
cannot hide a failed subtask. Fit once with a frozen optimizer/budget; no
hyperparameter grid on exposed validations. A candidate compatibility score is
the average log likelihood of that candidate's applicable edit events under the
predicted distribution. This creates a concrete candidate-history interaction.

High compatibility means "resembles the next observed action", not "safe",
"helpful", "correct" or "educationally effective". Do not automatically add
this score to the repair ranker using an outcome-tuned mixing coefficient.
Integration requires a separate frozen development comparison that preserves
correctness/non-regression endpoints and reports behavioral compatibility as a
distinct objective. A copy/repetition-heavy behavior target may be unhelpful;
that is a possible negative result, not grounds to remove such examples.

## 7. Minimum controlled train-only protocol before any repair integration

Use the same fixed source-qualified cohort for all five arms:

1. `C0`: literal current code/current nominal verdict only.
2. `Cn`: C0 plus shared count/elapsed-time/source-size nuisance terms.
3. `H`: Cn plus authentic full-history state and candidate interactions.
4. `U`: Cn plus exactly matched different-user, strictly-past training history.
5. `HS`: Cn plus a fixed hash-seeded permutation of authentic prior records;
   current remains anchored, all records and repeats remain. Shuffle only the
   encoder's counterfactual ordering after authentic provenance validation.
   Never rewrite timestamps or present shuffled order as observed history.

Use five deterministic **user-grouped** folds within the existing train split,
with the same user assigned to one fold across problems and all prefixes.
Training targets can be future relative to their own current prefix, but never
enter any features or another fold's fitted parameters. Rebuild donor matching
using fold-training users only. Report exact-current-source overlap and a
cross-user/same-current/different-history stratum; do not mistake style or repeat
memorization for personalized effectiveness. Problem-held-out analysis is a
separate generalization question, not a replacement for the user boundary.

Before results, freeze: feature/event taxonomy and hash dimensions, all five
arms, fold salt, parser/runtime versions, optimizer/regularization/seed/epochs,
user and missing-label weights, donor algorithm, primary NLL estimand, and all
resource/stop gates. A reasonable bounded implementation candidate is fixed
SGD log-loss/L2, alpha `1e-4`, seed `2027`, 20 manually shuffled epochs, with
train-only scaling and a predeclared Laplace constant for a one-class event;
this is a proposed configuration, not an already approved empirical protocol.
Report example exposures, users, prefixes and events rather than only steps.

Prespecify H−Cn, H−U and H−HS contrasts; H−C0 is secondary. Equal parameter
dimensions do not ensure equal effective capacity when C has zero history
inputs, so U and HS are necessary controls. No claim of history benefit follows
from H beating C0 alone, and a history effect on next-edit prediction is still
not a learning effect. Fold uncertainty, source-selection bias and rare-event
support remain visible. No repeated validation search or best-arm promotion.

## 8. Bounded continuation and non-negotiable stops

The narrower source-recovery stage has completed and passed independent audit;
see `zpd-train-successor-completion-audit-20260923.md`. All71,191 training prefixes
are retained, with71,190 certified source targets and one ambiguous successor.
The immediate next action is implementation and freezing of the event/state
encoder and all five controls, not more GPU repair generation or another risk
threshold. An independent protocol/code audit can then release one fixed
train-only history-action crossfit. Any new source/identity/missingness blocker
must preserve the frozen cohort; do not invent successors or reinterpret a
convenient subset as complete. C0 completion alone does not authorize a fit.

If history-action prediction improves, proceed only to a separately fixed repair
integration experiment with unchanged safety/correctness gates. If it does not,
retain the negative result and diagnose event support/representation rather than
weakening the claim's benchmark. Educational learning effectiveness ultimately
requires observed or controlled instructor/learner evidence such as a randomized
scaffolding study with retention/transfer; current repositories cannot supply
that outcome by relabeling code edits or testcase passes.
