# Observed feedback access boundary and generator-visible statement samples

2026-09-24. Bounded source/protocol/manifest-only inventory. This supplements
`zpd-observed-testcase-feedback-inventory-20260924.md`; it does not release
outcome access, extraction, code execution, fitting or a new empirical protocol.
Repository HEAD observed during this inventory:
`645812e5700e04f6978770bd0962b9c2448b3960`.

## Decision

There is **no verified public/sample inference testcase suite for the current
train320 repair interface** in the inspected metadata. Promoting the existing
full scoring suite into new input feedback is not authorized by the old design.
Suite availability on disk and the word “observed” do not establish a public
feedback entitlement or what an original participant saw.

A narrower prospective route exists: deterministically extract only explicitly
marked sample input/output text already present in the **sealed generation
request's `problem_description`**. Every bank generator received that field.
This would use already supplied statement information computationally rather
than reveal full scorer tests. Actual sample availability and extraction
fidelity remain **UNKNOWN**, because no description/request/test body was read.
The precise provisional name is **generator-visible statement-sample feedback**,
not certified original judge feedback or a recovered public judge test suite.

## 1. Three interfaces must not be conflated

| Interface | Inputs allowed/implemented | Testcase access conclusion |
|---|---|---|
| Fixed development bank generator | `scripts/generate_zpd_repair_banks.py:49-53` requires exactly `bank_id`, `problem_id`, `current_source`, `problem_description`, `time_limit`, `memory_limit`; lines 86-89 create one current submission with verdict `Unknown` | No history, nominal verdict, testcase feedback or evaluator input is passed |
| Observed repair ranker | `ObservationSource` contains submission ID, timestamp, exact bytes/SHA and nominal verdict; `PilotObservation` validates prior/current chronology. Source-only support adds original declared language and certified donor history | No testcase vector is part of this frozen input contract; a new feedback field requires a new versioned protocol/interface |
| Generic canonical-v5 prompts/inference | `src/repair/prompts.py:24-35` can attach `current_tc_outcomes`, pass rate and related fields; `_execution_feedback` renders them; generic candidate selection loads the supplied `data_root/<problem>/testcases.jsonl` | Capability to consume arbitrary feedback does **not** certify its visibility/provenance or authorize it for the new fixed-bank ranker |

The saved original and expansion generation manifests explicitly say
`D current only; verdict Unknown` and pin the same generator/prompts/inference
sources. Prompt D's general prose mentions observed execution “when available,”
but the fixed generator supplies none. Conversely, do not describe the entire
repository as nominal-only: generic canonical interfaces are broader.

The original pilot design (`zpd-repair-pilot-design-20260916.md`, sections 2, 5
and 6) specifies label-blind top-one ranking without additional execution;
candidate execution is the independent evaluator's job. It explicitly says
future hidden-test replay is research evaluation, not historical participant
feedback. The executed development protocol
`zpd-repair-development-20260918.md` likewise separates current-only generation
from full `data/<problem>/testcases.jsonl` evaluation. Later reuse of its labels
does not convert that full universe into an inference input.

## 2. CodeNet/AtCoder/AIZU visibility provenance is insufficient

`src/codenet/builder.py` expects a supplied CodeNet layout containing
`metadata/problem_list.csv`, `problem_descriptions`, and `test_cases`. Its
mapping at lines 321-358 only handles rows with `dataset == 'AtCoder'`:

- It first uses contest/task-name hints, or matches HTML sample pairs to
  sample-looking filenames in test bundles.
- `_looks_like_sample` (line 486) is a filename regular-expression heuristic,
  not a visibility certificate. It is used for identifying the **bundle**.
- `_write_testcases` (line 472) subsequently writes **all pairs in that bundle**,
  assigning synthetic IDs `case_00001`, etc. It keeps only `case_id`, `input`,
  and `expected_output`, losing original filenames, sample flags, origin URL,
  release/time-of-publication information and visibility roles.
- `_write_problem_metadata` (line 208) emits only time/memory limits. The three
  inspected problem metadata files (`p02623`, `p02629`, `p03086`) have exactly
  those two keys, consistent with the writer; they provide no dataset/source
  or public/sample/full/hidden role.

Therefore the local full testcase file cannot be called “public samples” from
its provenance. The builder source establishes an intended AtCoder mapping, not
the complete original release/download lineage. No AIZU public-sample mapping or
visibility certificate for this cohort was established. No statement or suite
body was opened to infer a dataset/task or sample identity. Download availability
today would not by itself show inference-time or historical learner access.

Repair evaluator manifests bind testcase file hashes, content-universe hashes,
runtime and executable/comparator sources. Those are integrity and execution
contracts, **not visibility contracts**; they have no public/sample selector or
per-case permission classification. Metadata does not resolve this gap.

## 3. An older observed/hidden partition exists, but means something different

`scripts/build_observed_hidden_evaluation.py:43-56` sorts testcase IDs by
SHA-256 of `seed:problem_id:case_id` and assigns the first ceiling-half to
“observed.” The rest is “hidden.” It does **not** identify original published
samples. Its scripts use separate `data-observed` and `data-hidden` roots for
candidate selection versus assessment. The source demonstrates that these
roles can be separated mechanically.

Located source routes include:

- `scripts/run_observed_hidden_unseen_remote.sh` → canonical-v5
  `eval/independent-hidden-v2`, seed 2027.
- `scripts/run_fse2027_seen_hidden_remote.sh` → canonical-v5
  `eval/independent-hidden-seen`, seed 52027.

The canonical evidence manifest records the Unseen partition's 54-row
`testcase-partition.jsonl` (SHA
`92aab86b0c7213fdc2c9c074655d7e7aacd969186c688b2d9724e7d018240e06`)
and its summary SHA
`e89659d5d0050c0380bcdf2a8843021982676a070241ae9c822b3621c2d8aee2`.
The partition/summary bodies are not present in the inspected local tree and
were not fetched. This is recorded historical metadata, not a fresh verification
of those artifacts or their applicability to train320.

The partition builder recomputes coarse verdicts from the observed subset to
avoid aggregate hidden-outcome leakage (`restrict_execution_feedback`, line 68).
It nevertheless copies `description.html` unchanged into both roots. Therefore
the source does not exclude a nominally hidden testcase being already present
as a statement sample. Whether that occurs is UNKNOWN here. No hidden-test
independence or new public-access claim should be based on this partition alone.
An arbitrary new partition of already exposed scoring cases is not a fresh
test suite or proof of original public availability.

## 4. Exact route for a future statement-sample inventory

### Stored descriptions and existing seals

Original current-bank requests are physically in:

```
outputs/zpd-repair-development-20260918/prepared-v2/requests.jsonl
```

Its SHA in the preparation and generation manifests is
`610d743374da20e52c98244eaef2e5f8e2205062095c55765811fbc49c8a7803`.
The family contains 96 original banks (train64 plus validation32); a future
exporter must enforce the frozen train-bank allowlist before using a record.
The present inventory did not open that mixed request body.

Expansion requests are in:

```
outputs/zpd-repair-risk-development-20260923/prepared-v1/requests.jsonl
outputs/zpd-repair-risk-development-20260923/prepared-v1/requests-{0,1,2,3}.jsonl
```

The whole train256 request SHA is
`03d1d6e8110fe19f0210d2e4356a2f0b33bdb953112f28ef8d7751937b2ded2a`.
The four chunk SHAs, recorded by preparation and corresponding generation
manifests, are:

```
0 bae7127c28b34cbd409978f888792337183df86342b7632a9e226b957c6ea854
1 f270503c8711856cdfe816b18306dcf1ce5db3fc9e429187caa0e4839c841847
2 ed02748d3df8e63d2d8f9df95c81e895b83b55b584b6ed3a4edf45dcb5613815
3 87d25963322a4abcb348dc17f5eeac367a44e0e41513e8a780194a3d7377f611
```

The original producer is `prepare_zpd_repair_development.py:77-86`; the actual
expansion producer is `prepare_zpd_repair_training_20260923.py:164-184`.
Both hash `description.html`, `metadata.json` and `testcases.jsonl` for provenance
but serialize only problem description/limits/current code into requests.
Hashing the full testcase file in that older preparation did not pass its
contents to generation or create permission for new feedback use.

### HTML-to-text transformation and loss

Both producers call `src/repair/dataset.py:_load_problem_context` (line 678),
which reads `data/<problem>/description.html` and feeds `_DescriptionParser`
(lines 93-115). The builder originally copied that HTML from
`<CodeNet source_root>/problem_descriptions/<problem>.html` (builder line 148).

`_DescriptionParser` preserves text including sample heading text and inserts
newlines at `p`, `pre`, `div`, `section`, `h1`, `h2`, `h3`, `li`, `br` boundaries.
But `text()` collapses intra-line whitespace to single spaces, deletes empty
lines, and strips outer whitespace. HTML structure, language attributes and
exact preformatted-byte boundaries are lost. The HTML read also uses UTF-8
`errors='replace'`. Thus exact original sample bytes cannot be assumed recoverable
from a request. Whitespace-sensitive or multilingual/ambiguous sections need
explicit unknown/rejection behavior, not silent repair from the full testcase
store or another source.

`build_messages` uses this entire request string (outer strip only) in Prompt D's
Problem Context; the fixed generator does not select sample sections or add
testcases. `_SampleParser` in `src/codenet/builder.py:43-83` and
`_extract_sample_pairs` at line 431 already parse **HTML** `h3` headings matching
English `Sample Input`/`Sample Output` plus an optional number and subsequent
`pre` text. They are bundle-mapping helpers, not a plain-text request parser.
They intersect indexes, overwrite repeated same-index sections and do not
certify original byte fidelity or reject every ambiguity. They cannot simply be
used unchanged as a certified request-sample extractor.

No dedicated sealed, strict, deterministic sample extractor for the actual
request text was found. The presence and completeness of sample markers in the
23 problem strings, consistent same-problem request descriptions, bilingual
duplication and whitespace ambiguity are all still UNKNOWN.

## 5. Minimal next authorization/evidence

The prospective **source-only** step can freeze a strict train320 request-bank
allowlist and parser before opening the authorized `problem_description` fields.
It should bind parent/preparation/generation hashes, exact description SHA and
offsets/spans for each extracted input/output section, parser version, sample
IDs and every ambiguity/missingness reason. It must never fetch descriptions,
testcase bodies or labels to fill gaps. Original validation32 request records
and all scorer/hidden/private-cache data remain outside the extraction output.

An initial inventory should report all320 coverage, all23 problem coverage,
duplicate/mismatched descriptions, no sample, unpaired/repeated headings,
unsupported grammar and whitespace uncertainty without reading submitted code
or executing a program. A separate release is required before replay. Since
request text already normalizes whitespace, preserve exactly the declared
request-derived representation and do not claim byte-faithful original samples
unless separately established under an approved source boundary.

All compared arms must receive the same statement sample information and current
sample feedback budget. A matched current-feedback control must distinguish
extra runtime information from the authentic historical pass/progress signal.
Unknowns and unsupported samples remain in the full cohort denominator. Do not
choose samples or grammar variants because they fix the previously observed
selection errors. Sample feedback may guide a new developmental method but may
not retroactively change frozen candidate labels, gates or completed results.

For a stronger claim that a suite was officially public at the original
submission time, additional evidence is required: authoritative release/task
mapping, publication/availability evidence and per-case role/content hashes.
That stronger claim is not needed merely to establish that the sealed bank
generator received a particular string; the two claims must remain distinct.

## Inspection hashes and limits

Source SHA-256 values:

```
src/codenet/builder.py                     bfeaee83523c60409ac25def9319907208240cfac8e91a0b19eac241b94fa105
src/repair/dataset.py                     4f88995489d439b69e672b922e2e0145abe6e75083c0285444fab6bb22012aaf
scripts/generate_zpd_repair_banks.py       3705c545e4c03aaabcfe9ee550df8068b58a7b63200b42c0e88a5e5726f4a691
src/repair/prompts.py                     09d16af33a986f9314cb468754f67241b0d1e2e53ebe9b27bbfb33381bbebdea
scripts/build_observed_hidden_evaluation.py bfd2202048717995e0d39f7746796919717a7f281448ece6e40649b6af674980
scripts/prepare_zpd_repair_development.py  60eb6d6e3ae9ff81fa315f300755c37c3036398086957b095a71ddcecad549e0
scripts/prepare_zpd_repair_training_20260923.py 34025dc1eedb2615e9e42625300dd7ad2aba7e1b29f0966cfa51ecca5c325c26
```

Preparation manifests inspected:
original `fd76a3a40df7df396e24c456b100d22ea0f13f2e6b5d92501ab2160a25e41bd8`,
expansion `6a13658d5409d817ad4655efa7fe8a31fa84ec65a2efb24a03086920baaac793`.
These and the generation manifest metadata were read; request bodies and their
current hashes were **not** read/recomputed in this inventory.

No submission, description, testcase/expected-output, label, mixed cache,
prediction or model body was opened. No remote lookup was necessary. No code,
source data, experiment or existing protocol was modified; no extraction,
execution, fit, test run or commit was performed. Only this document was added.
