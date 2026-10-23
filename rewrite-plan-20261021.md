# Final manuscript rewrite contract

This is a writing-only revision after the experiment cutoff. No training,
generation, testcase execution, new selection, or experiment resumption is allowed.
Existing evidence and its frozen denominators/gates remain unchanged.

## Story and scope

ZPDPatch mines trajectory-conditioned repair targets, trains independent
policies, and selects executable candidates. Matched controls distinguish
target-induced locality from candidate breadth; neither the canonical tests nor
the completed adaptive development runs establish an authentic-history repair
advantage. Retain canonical-v5, recommending current-only Answer-3Seed within the
tested historical deployment stack, without renaming that baseline as a new ZPD
algorithm. Current-only Answer-9Choose3 has the higher observed Unseen RR (82.0%
versus 81.2%); the recommendation is not dominance on every split.

Three contributions: an explicit trajectory-dependent hypothesis and its
controls; the Mine / Train / Select construction and executable selection
contract; the matched evaluation and complete negative-development accounting.
Peer-target matching is a separate control, not a mandatory pipeline stage.

## Structure

1. Introduction: advances, history-dependent hypothesis, identification challenge,
   Mine / Train / Select, outcomes, exactly three contributions.
2. Preliminaries: state and execution evidence, generic controller, limitation and goal.
3. Our Approach: overview, algorithm, Mine, Train, Select, matched controls.
4. Experiments: settings; RQ1 effectiveness; RQ2 target construction and locality;
   RQ3 component efficacy; RQ4 generality; RQ5 development diagnosis; threats.
5. Related Work: repair, histories and educational constructs, execution selection.
6. Conclusion; Data Availability. AI research-use disclosure belongs in methods.

## Visual plan

- Inline monochrome overview and two algorithms.
- Data table, full-test result table, matched-target table, edit-budget table,
  current-only factorial table, generality analyses, and separate two-slot development table.
- The eight-draw development bank is a distinct comparison, not a row in the
  canonical RR ranking. DPO training is explicitly unevaluated.
- Tables precede their first textual references; single-column floats use [h].
- All prose and visuals remain inline in main.tex, one prose paragraph per line.

## Evidence and validation

Primary sources: the final methodology report and deadline inventory; current-only
deployment ladder; corrected paired-target and factorial results; paired Java;
peer-target control; selected-portfolios and consolidated result bridge.
Preserve exact uncertainty intervals and do not treat test passing or locality
as educational benefit. Hash/exit tests are provenance checks, not scientific outcomes.

Updated venue at the user's explicit request on 2026-10-21: ICSE-SEET 2027 Research Paper.
https://conf.researchr.org/track/icse-2027/icse-2027-software-engineering-education-and-training--seet-
The SEET CFP requires `\documentclass[10pt,conference]{IEEEtran}`, without
compsoc/compsocconf, a 24pt title and 10pt body, at most 10 body pages plus 2
reference-only pages. Use IEEE numeric citations and two columns. Include Data
Availability within the 10-page body; do not import the FSE page-count exemption.
Do not shrink spacing or body fonts to meet the limit. Preserve detailed negative
results in the retained final report when condensing the manuscript.

Rebuild the PDF; verify evidence bindings, page boundaries, references, float
reading order, fonts, and all rendered pages. This is not a paper review or an
Overall Merit assessment. An independent review requires a separate turn and a
fresh history-free reviewer under AGENTS.md.

The old Korean translation is preserved and explicitly marked as predating this
rewrite; it is not silently presented as a synchronized final manuscript.
