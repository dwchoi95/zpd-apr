# Exact-splice generation: bounded representation/capacity pilot

## Evidence and decision fixed before execution

Balanced diagnosis release 822ef91a490204af2c37492975871b08e10572f420f73614daee2f854de21de9
completed normally at 2026-10-17 03:53:55 KST. Outer seal:
93e29252d0dc27fe502a9486199484e28f0085fc2386da0d406f9a76a0f91391.
All 2,160 candidate sources are now observed (31 unstable, preserved unknown).
H selected AC remains 200; known available AC is 207, with 97 proven no-AC
recipients and 16 unresolved recipients. Only 4 of 17 H regressions have an
alternative known non-noop safe candidate. C/H/HS/U AC availability lower bounds
are 204/207/204/202. Original selected AC/regression/unknown and HOLD remain.
This supports investigating candidate production, not another tie-rule sweep.
It does not prove copying is the cause or authentic history is beneficial.

## One implemented candidate-production change

Represent output as an ordered JSON array of original-current line splices:
[[start,end,replacement_text],...]. Offsets are zero-based half-open ranges of
splitlines(keepends=True). They always refer to the original current program.
Use deterministic SequenceMatcher(autojunk=False) non-equal opcodes for gold
targets, with the prior rstrip target normalization. Parse strict JSON, require
integer in-range ordered nonoverlapping ranges, and reject invalid output;
never repair malformed output, silently return noop, or retry a draw. Valid
splices copy every unmentioned original span exactly. This is a syntactic
identity guarantee outside declared edits, not proof of semantic safety,
small patches, pedagogical benefit, or correct generated line indices.

Replace only the system output contract. Preserve the full byte-framed user
message, every prior program, public evidence, common C/H order and paired target.
The later proposed model will learn splices with uniform target-token CE; this
is a representation/objective package, not an isolated loss-weight ablation.
No training, generation or evaluation claim is made by the present pilot.

## Pilot population and barriers

Reuse the sealed 19,199 train and 4,365 validation examples for each C/H arm.
Check lossless reconstruction and source/message bindings for every example.
Tokenize all converted C/H rows without truncation or history limits; use the
existing 4,096 input / 4,096 output / 8,192 full limits. No new exclusion,
resampling, split change, or target-dependent selection is allowed. If any row
does not fit, publish HOLD with every overflow and do not probe or fit. Report
old/new target-token counts descriptively, not as performance improvement.

If every row fits, run only the existing fresh-model forward/backward capacity
probe on the longest common paired batch, once per arm, batch 2, same base,
LoRA and seed 2027. No optimizer update, adapter publication or retry. Successful
normal child exits, exact source/model/input hashes and empty child cgroups
are required. Limits: materialization 2h/16GiB; capacity 1h/64GiB; coordinator
3h15m. All paths below /home/cdw/VSCode/zpd-apr. Keep negative outputs and dirty
canonical checkout unchanged; use a separate clean snapshot.

## Follow-up decision

A passed pilot permits the next separately frozen matched C/H one-epoch fit,
then strict splice decoding into the unchanged C/H/HS/U two-draw selector and
private evaluator. Freeze conversion/failure handling before any performance
measurement. Keep all 320 evaluation recipients and unknowns. Do not alter the
existing pooled/fold/regression/uncertainty gate or tune on private labels.
A blocked pilot requires a separate documented engineering decision, not
automatic filtering or retry. This exposed adaptive cohort cannot establish
independent generalization, ZPD learning benefit or model promotion.

Register this pilot family/release with the existing at-most-once completion
bridge before launch, preserving all previous deliveries and permission policy.
The completion callback selects the next task after actual normal exits; a
pilot pass is not an experiment success claim. Hourly unchanged-status Mac
notifications and durable Korean reports stay enabled.
