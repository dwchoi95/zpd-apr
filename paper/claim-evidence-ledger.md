# FSE 2027 Claim-Evidence Ledger

One-sentence story: ZPDPatch separates target construction from candidate selection: on two Python splits, matched-source Progress targets trade coverage for locality and matched peer replacement increases coverage; fixed-decoder breadth is a distinct, separately measured contributor, not a universal explanation of improvement.

| ID | Claim | Scope | Actual evidence | Claim verb | Principal threat |
|---|---|---|---|---|---|
| C1 | Candidate breadth is a major confound in execution-guided APR comparisons. | 997 Seen and 250 problem-held-out Python instances | Same-draw one-versus-three decomposition, temperature sweep, breadth-cost curve | demonstrates | One model family and benchmark |
| C2 | The framework separates output sampling, checkpoint diversity, pool selection, target construction, and history serialization. | Frozen A1-T1-S3-A3-A9-M9 ladder and paired controls | Decoding-matched checkpoints, Base x3, five-fold selection, paired-target and Full-versus-Current controls | introduces | Some contrasts remain post-hoc |
| C3 | Current-only Answer-3Seed is the best tested unrestricted learned deployment. | Canonical Seen and Unseen tests | 72.0% Seen and 81.2% Unseen RR | outperforms | LSGen remains stronger on Seen unrestricted RR |
| C4 | Progress targets do not improve unrestricted coverage over Answer targets when source distribution and count are fixed. | 7,389 paired train and 931 paired validation examples; common Seen/Unseen evaluation inputs | Progress-Answer RR -19.2 points Seen [-22.96, -15.54] and -11.2 points Unseen, both problem-cluster intervals excluding zero | demonstrates | Target semantics and induced target distance cannot be separated |
| C5 | Progress targets produce smaller and more source-preserving joint repairs under that matched control. | Jointly repaired paired-target outputs | Answer-Progress TED +10.08 Seen and +6.83 Unseen; Progress token retention +5.6/+6.5 points and line retention +8.9/+10.4 points | demonstrates | TED and retention do not measure pedagogical value |
| C6 | Mixed-target constrained-coverage gains are not robustly replicated. | Six fixed TED budgets, 1.5B, problem holdout, and CodeWorkout | Cross-setting intervals and reversals reported in RQ3 and RQ4 | shows | Power varies by setting |
| C7 | Same-user provenance is not the source of Progress coverage in the matched design; outcome-equivalent peer targets improve it. | 5,231 train and 306 validation examples per condition; canonical Seen/Unseen tests | Exact source/outcome matching, token-distance caliper, three independently trained seeds; peer minus same-user RR +4.3/+6.0 points | demonstrates | Unmeasured target structure and style can differ within calipers |
| C8 | Current-only Answer-3Seed effectiveness is not confined to the last-failure endpoint within eventually successful trajectories. | 2,770 Seen and 674 Unseen executable non-AC prefixes | Early/middle/last RR 70.0/67.6/71.4% Seen and 82.9/77.3/81.8% Unseen with overlapping problem-cluster intervals | shows | Never-successful trajectories remain unmeasured |

## September 15 audit amendment

The raw outcomes underlying C1-C8 are unchanged. Their interpretation must reflect the following verified corrections; this amendment supersedes any stronger causal reading above.

- Existing breadth-control and breadth-extension runners read full-history datasets. Prompt style D does not remove history. The new `analysis_protocols/fse2027-review-20260915.json` declares a separate current-only four-cell comparison; no result is available yet.
- C5 is supported on two Python splits, not directly replicated by the old Java or 1.5B portfolio contrasts. Direct matched-target Java retraining is pending.
- C7 estimates replacement under the entire matching rule, not isolated provenance causality. All 5,231/306 donors come from the recipient's train/validation split; donor identifiers, code and outcome linkage pass the record audit, with no train-validation donor overlap.
- `fse2027-peer-distributions.json` reports pre-match, excluded, same-target and peer-target distributions. Train mean token distances are 118.06/118.69 and mean defined AST distances 116.64/118.81 (5,154 pairs). Validation values are 136.98/137.37 and 134.59/134.73 (300 pairs). Target length and reuse remain different.
- `fse2027-review-consistency-audit.json` reproduces both paired-target selectors without mismatch. After the whitespace correction, 21 Seen and 20 Unseen joint repairs have unparseable source code: included in unrestricted RR, excluded from defined-TED summaries. Finite budgets reject undefined-distance changes.
- Historical `FSE2027_COMPLETE` seals an earlier revision. It does not certify these changes or the pending experiments.

Abstract, Introduction, Results, Threats, and Conclusion must preserve these scopes and distinguish completed from pending evidence.

## Completed addendum (supersedes pending status above)

- Direct student-disjoint Java retraining: Progress 92/181 (50.8%), Answer 155/181 (85.6%). Progress-minus-Answer RR -34.8 points, student CI [-44.91, -25.47], exercise CI [-47.31, -23.79]. On 90 joint repairs, Progress lexical retention +4.8 points, student CI [2.79, 7.19], and line retention +5.1, CI [2.92, 7.25]. This strengthens C4/C5 outside CodeNet; it does not replicate C7 or educational utility.
- True current-only, all-vLLM cells: one greedy 53.1/67.2% Seen/Unseen; three greedy checkpoints 62.9/78.0%; stochastic same-checkpoint 66.8/79.6%; stochastic distinct-checkpoint 68.9/80.8%. Distinct-minus-same +2.1 [0.00, 4.16]/+1.2 [-2.93, 5.93]; Seen problem-balanced CI also crosses zero. C3 is limited to its tested historical Transformers stack, not a backend-independent deployment ranking.
- A syntax-significant leading-space repair was masked by `.strip()` comparison in one current-only Answer output and three historical paired-target Progress outputs for the same input. Original files remain intact. Corrected paired-target Seen Progress RR is 34.0%; the contrast is -19.2 [-22.96, -15.54] points. Seen joint repairs increase to 299, of which 278 have defined source TED (21 undefined); Unseen remains 154/134. Locality directions and displayed means are unchanged.
- Updated paper numbers are literal LaTeX, verified by expanding the curated bindings in `paper/main.evidence-bindings.json` against the manuscript. The only user-defined `newcommand`s are the four naming macros `\tool`, `\progress`, `\strict` and `\answer`; no result value is a macro. The independent review is conducted on that PDF without supplying this ledger.
