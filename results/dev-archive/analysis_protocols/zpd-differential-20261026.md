# differential-20261026-v1: plausible patches on generated inputs (RQ1 benchmark)

Authorized by `zpd-deadline-extension-20261023.json` (user instruction of 2026-10-24 allowing new experiments; on
2026-10-26 the user approved the overfitting check proposed after the ICST framing analysis). Execution only, on the
local machine, because the server's judging phases of review-peer-20261026-v1 must not share the CPU with another job.

## Why

Every repair is judged by the FixEval test suite it was gated on, so a returned patch is only plausible. ICST repair
papers measure how many plausible patches overfit that suite; the reviewers will ask the same.

## Design (fixed before execution)

- **Inputs:** for each of the 14 RQ1 problems, a generator written from the problem statement's constraints produces
  random inputs (fixed seed), mixing small and boundary cases. Problems whose statements accept several outputs are
  judged with the checker their statement implies, or excluded if none is possible, and the exclusion is reported.
- **Reference:** the output that most accepted programs of the benchmark's students (their own accepted targets) agree
  on; an input on which they disagree is dropped.
- **Patches:** every patch that passed the full test suite, for ZPDPatch and the five existing configurations
  (`output/approaches/*.jsonl`), run with 2.5 s per input.
- **Reported:** per technique, the share of plausible patches that fail any generated input, and the same within
  reach; the inputs, references, and per-patch outcomes are kept.

## Not changed

Every reported result of earlier families; the FixEval suites, the gate and the denominator.

## Result (2026-10-27)

Completed normally on the local Mac (2026-10-26 19:50 to 2026-10-27 00:36 KST); 5,634 distinct plausible programs on
100 inputs per problem; no problem excluded, no input dropped; `MANIFEST.sha256` verified. Share of plausible patches
failing any generated input: ZPDPatch 10.5%, Refactory 9.5%, BRAFAR 8.1%, MENTORED 8.1%, LSGen-Qwen 5.5%, LSGen-GPT 6.1%.
Failures concentrate on inputs the FixEval suites lack (p02742: products above 2^53 break float division, which also
breaks 2 of the 7 reference programs). TLE was sensitive to machine load (another project ran on the Mac).

## Amendment (2026-10-27, before any further execution)

Because ZPDPatch is trained toward the student's own accepted program, a latent bug of that program can reappear in a
patch. Each benchmark student's own accepted program (`target_code`) is run on the same 100 inputs with the same harness,
and a patch counts as overfitting beyond the student's own fix when it fails an input that the student's accepted
program passes. Reported per technique, overall and paired on the same buggy programs.

## Amendment result (2026-10-27)

Students' own accepted programs fail some generated input in 199 of 1,753 cases (11.4%). Counting only failures on
inputs the student's own accepted program passes: ZPDPatch 3.1%, existing techniques 3.4-6.5%; paired exact McNemar
p < 0.05 only against Refactory (0.0052). Reported in Threats (5) of the paper.
