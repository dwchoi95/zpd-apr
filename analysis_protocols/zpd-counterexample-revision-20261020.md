# Public-failure counterexample repair (adaptive development)

## Evidence and decision fixed before this run

The revision diagnosis completed normally at 2026-10-20 00:27:52 KST, with
320/320 recipients, 644/644 missing sources and 53,772/53,772 case attempts.
Its sealed report has SHA-256
`10d2333d00f8cf76c728050b9c8f5390b04ea29bec55a82e4464d47e3b3f24eb`.
Selected AC C/H/HS/U stays 194/193/192/202; regressions 12/10/13/14 and
unknowns 14 each. HOLD remains HOLD. H's known candidate oracle is only 197
(upper 211 with unknowns), with four known AC choices missed. Selection is
not the principal established bottleneck. In H's original public-failure
stratum, 25/87 second draws exactly copied the failing first source; 13
became privately AC. In its public-pass stratum, jointly stable comparisons
gained six AC and lost 17, with 17 introduced and two prevented regressions.
These are descriptive, not causal effects of feedback, and all negative
results remain preserved.

## One bounded successor policy

Restore the original full-source C/H adapters and original 320 recipients,
four arms, five folds and two slots per arm. Reuse original draw zero exactly.
For each arm independently, inspect ONLY the original stable public sample
mask of draw zero. If at least one sample fails, regenerate draw one with
the original full prompt/history, rejected proposal and exact statement
sample inputs, expected outputs and stable observed verdicts. Actual program
stdout is unavailable and is not invented. Failed and passing samples are
both shown. The instruction asks for root-cause correction rather than
copying the failing proposal, while retaining correct original behavior.
The generated proposal is explicitly not student history. Original current
code remains last; original history bytes are never truncated.

If all public samples pass, or evidence/source is unavailable, retain the
original independent draw one byte-for-byte, including failure rows. Do not
substitute the later unconditional-revision result. Exactly C=80, H=87,
HS=82, U=85 second slots require new generation: 334 total. The other 946
second slots and all 1,280 first slots are reused. Exactly 2,560 terminal
slots remain. No retries, new third candidate, format repair, dedup rejection,
private-result routing, per-problem exception or outcome-tuned threshold.
If a newly generated source still copies the failing source, retain it.

This is one conditional policy package, not a pure single-factor prompt
ablation: it changes when feedback is used and how counterexamples are shown.
The routing rule is identical in C/H/HS/U and never depends on arm, donor
identity, private correctness, selector score or final gate. Sample evidence
already belongs to the public specification; no additional dataset is added.

## Frozen controls, lifecycle and reporting

All model hashes, seeds, sampling (.8/.95), 4,096 output tokens, 8,192 context,
4,096 input budget, C_joint selector, four-block execution, private test set,
unknown handling and development gate remain unchanged. Overflow becomes a
terminal resource failure, never filtering or truncation. Original full-source
results 209/192/198/206 and unconditional revision 194/193/192/202 remain
visible; all arms and safety outcomes must be reported, even if unfavorable.

Freeze source, input, audit, tokenization and release before new generation.
Run only in a new isolated snapshot and
`outputs/zpd-counterexample-revision-20261020` under the authorized project.
Use the existing bounded generation/public/private coordinator with normal
exit, cgroup cleanup, full artifact inventory and drift barriers. Authenticate
the immediate diagnosis before starting and refuse duplicates. Register the
exact release in the existing observer, preserve event latches and verify
an actual live read. No change to dirty canonical checkout, deletion or push.

This is adaptive development on an exposed cohort, not confirmation, learned
educational effect or guaranteed improvement. Compute is not identical:
cached candidates come from an earlier run, only the failing branch generates
new text, and public/private execution is rerun unchanged. Neither an AC gain
alone nor this policy's motivation establishes a history effect. Do not
unlock held-out evaluation or promote a model on this experiment alone.
