# Independent source-roster implementation review

2026-09-24, approximately23:16 KST. Root reviewed the new implementation authored
by a different agent. This is not a review of root's statement parser, a paper
review, an experiment release, or evidence of repair improvement.

Reviewed complete source and tests:

- `scripts/zpd_observed_source_roster.py` SHA256
  `986d90b202abdfb1d188fa35300cb5f485da55f1712d45d214a718bbc557d52d`.
- `tests/test_zpd_observed_source_roster.py` SHA256
  `2cec70974bda1b052a1fdc88224b2edf116c61dfa19f35e341e94ab3cd6a4acb`.

**Scoped decision: PASS for the pure authenticated-join roster transformation;
production preparation and submitted-source execution remain unreleased.**

The builder preserves exact UTF-8 bytes, full source identities, owner, language,
nominal verdict, timestamp and every recipient/prior/donor context. Deduplication
is confined to execution requests keyed by problem/SHA/language; distinct source
IDs and repeated context membership remain. Source identity conflicts, nonfinite
or Boolean timestamps, strict chronology violations, invalid/current/donor IDs,
conflicting problem folds, duplicate recipients/users/banks and unknown schema
fields fail closed. Non-Python and empty sources are retained, not reclassified.

The immutable output does not alias mutable input containers. JSON serialization
uses exact source hex and includes `execution_authorized=false`. There is no I/O,
subprocess, network, evaluator, label reader, model, fit or production CLI.

Root independently reran all17 roster tests together with22 parser tests:
39 passed in0.778s. Root also independently reconstructed expected sources,
membership and execution groups directly from the upstream synthetic fixture's
raw selected observation records, rather than using the new builder to construct
its expected answer. All50 source records,50 full context tuples and40 deduped
execution groups matched exactly. No donor-current source was newly requested.
This was synthetic-only; no empirical source/description/testcase/result body
was opened by these checks.

Limits are explicit and acceptable for this pure layer: historical-source
authenticity, current-language Python and donor-own-cutoff checks are inherited
from the separately certified upstream join. The returned join does not contain
the donor's current timestamp; this builder correctly does not invent one.
Its own recipient cutoff checks do not replace that upstream certification.
The later production caller must verify the exact320/23/five-fold cohort, source
closure and all original input bindings. A caller passing arbitrary look-alike
rows would not thereby acquire valid provenance or execution permission.
