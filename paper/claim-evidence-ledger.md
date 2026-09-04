# FSE 2027 Claim-Evidence Ledger

One-sentence story: Although execution-guided selection can raise repair coverage, it conflates supervision with candidate breadth; we present a matched identification framework instantiated by ZPDPatch and show that breadth dominates unrestricted coverage while trajectory-derived Progress targets reproducibly trade coverage for smaller, more source-preserving repairs.

| ID | Claim | Scope | Actual evidence | Claim verb | Principal threat |
|---|---|---|---|---|---|
| C1 | Candidate breadth is a major confound in execution-guided APR comparisons. | 997 Seen and 250 problem-held-out Python instances | Same-draw one-versus-three decomposition, temperature sweep, breadth-cost curve | demonstrates | One model family and benchmark |
| C2 | The framework separates output sampling, checkpoint diversity, pool selection, target construction, and history serialization. | Frozen A1-T1-S3-A3-A9-M9 ladder and paired controls | Decoding-matched checkpoints, Base x3, five-fold selection, paired-target and Full-versus-Current controls | introduces | Some contrasts remain post-hoc |
| C3 | Current-only Answer-3Seed is the best tested unrestricted learned deployment. | Canonical Seen and Unseen tests | 72.0% Seen and 81.2% Unseen RR | outperforms | LSGen remains stronger on Seen unrestricted RR |
| C4 | Progress targets do not improve unrestricted coverage over Answer targets when source distribution and count are fixed. | 7,389 paired train and 931 paired validation examples; common Seen/Unseen evaluation inputs | Progress-Answer RR -19.3 points Seen and -11.2 points Unseen with problem-cluster intervals excluding zero | demonstrates | Target semantics and induced target distance cannot be separated |
| C5 | Progress targets produce smaller and more source-preserving joint repairs under that matched control. | Jointly repaired paired-target outputs | Answer-Progress TED +10.08 Seen and +6.83 Unseen; Progress token retention +5.6/+6.5 points and line retention +8.9/+10.4 points | demonstrates | TED and retention do not measure pedagogical value |
| C6 | Mixed-target constrained-coverage gains are not robustly replicated. | Six fixed TED budgets, 1.5B, problem holdout, and CodeWorkout | Cross-setting intervals and reversals reported in RQ4/RQ6 | shows | Power varies by setting |

Claim lock: C1-C6 may change only when their underlying artifacts change. Abstract, Introduction, Results, Threats, and Conclusion must preserve the same scope and direction.
