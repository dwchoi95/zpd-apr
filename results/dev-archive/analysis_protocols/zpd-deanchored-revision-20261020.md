# Withhold failed generated proposals: bounded de-anchoring test

## Evidence, not a success claim

Counterexample revision completed normally at 2026-10-20 02:43:38 KST.
All 320 recipients and 87,540 private testcase attempts completed. Its outer
seal SHA-256 is `c585b18697f47a14d7b59f01e4a7f5760c54dfc10571123da14f0b6876c200df`.
Selected AC C/H/HS/U is 197/188/191/202, regression 12/12/12/15, and unknown
12/12/11/11. H is below all controls and nonworse than C in only one of five
folds. The original gate is HOLD. H was 192 under uniform independent draws
and 193 under unconditional revision; this successor is not an improvement.

The explicit counterexample prompt still copied the failing H proposal in
25/87 cases, exactly the previous unconditional revision count. It passed
public samples in only 16/87, versus 19/87 previously. This directly observed
copy failure justifies testing whether access to failed generated code anchors
the next generation. It does not prove that anchoring caused the lower RR.
Unselected private candidates remain incompletely measured; no complete-bank
oracle or causal feedback effect is claimed. Preserve that uncertainty.

## Intervention fixed before generation

Use the identical original public masks and public-failure routing as the
counterexample release. For the same 334 failing second slots, retain the
exact public sample input, expected output, observed proposal verdicts and
source hash, but remove ONLY the generated-proposal code section. Clarify
that these verdicts describe the withheld proposal, not the student's current
program. Ask for repair from the specification, original current program and
all supplied student history. Do not delete, summarize, filter or truncate
any student submission. Original current source remains the exact final bytes.
If the withheld proposal happens to equal a supplied student source, preserve
the student source; this intervention removes a role-specific frame, not
every textual occurrence of that program.

Retain the same first 1,280 slots and original independent second 946 slots
byte-for-byte, including errors. Exactly C/H/HS/U 80/87/82/85 second slots
are newly generated. No resampling of the latest failed outputs, no third
candidate, private-outcome routing, threshold sweep, format repair or retries.
New second slots keep the original per-slot seeds and adapter assignment.
The code representation and generation engine are unchanged except the
proposal display and its explanatory instruction. Identical sources produced
again remain valid terminal attempts; never retry them to force diversity.

## Fixed controls and execution

Same 320 recipients, five folds, C/H/HS/U, source histories, original C/H models,
two candidates, .8/.95 sampling, 4,096 output/input budgets, 8,192 context,
C_joint selector, runtime/testcase hashes, four-block evaluation, unknown
handling and development gate. Input overflow remains terminal resource
failure. Freeze tokenization/source/input/audit/release before model generation.
Report all arms and original uniform, unconditional and explicit-counterexample
comparators. A lower copy count alone is not a passing criterion or improvement.

Fresh namespace only: `outputs/zpd-deanchored-revision-20261020`. Verify actual
normal exit and all artifacts of the predecessor before launch. Bounded
generation/public/private services use the existing seals, source checks and
cgroup cleanup. No canonical dirty-checkout change, deletion or publication.
Register this exact release in the existing observer and verify a real read.

This is adaptive exposed-cohort development. Changed prompt length, small
instruction changes and different execution blocks prevent a pure semantic
causal claim. No educational benefit, confirmatory history effect, model
promotion or paper acceptance is inferred. Keep the frozen gate unchanged.
