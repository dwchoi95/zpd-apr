# Statement-sample parser: independent synthetic review

2026-09-24. Reviewer: independent of the parser/protocol author. This is a
source-level parser review, not a paper review, empirical preparation, submitted
program execution, or release to fit a model.

## Boundary and materials

Read the complete `zpd-statement-sample-preparation-20260924.md` specification,
`scripts/zpd_statement_samples.py`, and
`tests/test_zpd_statement_samples.py`. No empirical request, description,
submitted source, testcase, target, label or outcome body was read. No remote
operation, fit or commit was performed. The reviewer edits only this document;
findings were sent to the author rather than patched into author code.

The parser is a pure bytes-to-extraction function. Its source has no file reader,
network client, executor or fallback suite access. SHA/request projection,
canonical paths, selected train membership and final provenance rechecks remain
the future caller's responsibility. A syntactically available extraction is
not a certified public test suite or usable execution feedback.

## Initial positive checks

`python3 -m unittest tests.test_zpd_statement_samples -v` passed all 15 tests on
Python 3.13.7. Tests cover strict UTF-8, immutable input, exact whitespace/line
endings, Korean text, one entity decoding, empty blocks, numeric ordering,
duplicates, all-or-nothing pairing, script/style exclusion, nested sample tags,
comments/declarations, missing blocks, unmatched/unclosed heading/pre structure,
case-insensitive headings and output-first pairing.

Independent additional in-memory fixtures confirmed escaped `&lt;script&gt;`
stays literal sample data, ordinary `x < y` is preserved, and nested markup or
unfinished declarations inside active samples is rejected. Standard numeric
invalid character references use the parser's standard single-decoding
replacement semantics, not a second unescape pass. A bounded 78-case set of
truncated delimiter/tag/entity fragments produced no unexpected exception and
no unavailable extraction carrying a partial sample subset. These are synthetic
properties, not coverage or correctness claims about the actual 23 statements.

## Findings sent to the author before release

1. **Self-closing non-void HTML structures.** The initial implementation accepted
   `<h3>Sample Input</h3><pre/><h3>Sample Output</h3><pre/>` as two explicitly
   empty blocks. A `pre` element is not an HTML void element; treating its
   slash as an XML closing tag is an undocumented extension of the conservative
   malformed/unclosed rejection contract. Requested rejection of self-closing
   heading/pre forms or an explicit prospective grammar decision, before any
   empirical statement inspection. Ordinary `<pre></pre>` must stay valid.
2. **Raw-text/inert ancestor boundary.** In-memory wrappers `<xmp>`, `<iframe>`,
   `<noembed>` and `<template>` around an otherwise valid sample pair were
   accepted. A tag-shaped string in raw text is not an actual `h3` declaration;
   template content is inert. Requested an explicit conservative exclusion or
   rejection policy and regressions. Current local `HTMLParser` already avoided
   recognizing samples inside `textarea` and `title`, but the boundary should
   not rely silently on runtime-dependent parser behavior.
3. **Heading inline syntax clarification (secondary).** An unclosed `span`
   inside a closed `h3` was accepted. The current heading recognizer collects
   text rather than validating arbitrary inline DOM structure. The author
   should specify permitted inline text markup or reject ambiguous forms; this
   review does not require a general browser DOM implementation.

Initial status: **pending those boundary decisions; no empirical release**.
The 15 green tests alone do not address the additional witnesses above. A final
verdict will identify the exact reviewed source/test hashes after resolution.

## First author revision and independent recheck

The author added explicit protocol rules, rejected self-closing non-void
structures, rejected markup in recognized headings, and excluded raw-text and
inert wrappers. All 21 revised unit tests passed independently. These changes
were made before empirical statement inspection, not in response to coverage.

An additional combined-context witness exposed incomplete ignored-context
nesting: `<template><xmp></template>` followed by a sample pair and
`</xmp></template>` was still accepted. In raw `xmp` text the first template
closing string is literal, so it cannot terminate the inert ancestor. The
same issue occurs with several other raw/inert inner elements and `plaintext`.
Requested a minimal fail-closed rejection of such mixed contexts rather than
general browser-DOM recovery. This remains the same raw/inert boundary finding,
not a request to expand the supported sample grammar.

## Final author revision, reviewed hashes and verdict

The author now rejects a different raw/RCDATA/inert element or `plaintext`
inside an inert subtree as `mixed_rawtext_in_inert_subtree`; same-kind inert
nesting keeps an explicit depth. The prospective specification explicitly
records this conservative unsupported-grammar rule. The original self-closing,
heading-markup and wrapper findings, including the combined-context witness,
are resolved in the reviewed source.

Final independent execution on Python 3.13.7:

- `python3 -m unittest tests.test_zpd_statement_samples -v`: **22/22 PASS**.
- Additional in-memory suite: **128 synthetic cases PASS**, including all 20
  mixed-inert escape combinations, ten wrapper-only versus wrapper-plus-real-
  sample pairs, five non-void self-closing rejections, five exact entity/empty/
  whitespace preservation cases, and the 78 truncated-fragment cases. No real
  input files were read by those fixtures.

| Reviewed file | SHA-256 |
| --- | --- |
| `scripts/zpd_statement_samples.py` | `e320ddee83b923c826a810fe53a3e41c2a96f5000bb79fef148ff38dde4b0b6e` |
| `tests/test_zpd_statement_samples.py` | `3bba0c7b36e71fde1c3a9227384d3dd388f0109067cf737be33a6e9bba0a9471` |
| `analysis_protocols/zpd-statement-sample-preparation-20260924.md` | `eb9a0e5c95ca3d3cbaa25f6b9fb5422a96d4ad3ce1106501498a6cc958e914bf` |

**PASS for the pure conservative parser contract.** No remaining concrete
blocker was found within this bounded review. This is not a proof of arbitrary
browser equivalence, a claim of actual sample coverage, or approval to execute
submitted programs. Unsupported/malformed grammar deliberately loses availability
rather than inferring data; the whole recipient/problem denominator must remain.

The preparation caller still needs its own independent review of fixed source
root and train allowlist, externally authenticated HTML/request SHA ancestry,
exact frozen projection comparison, all-problem/all-recipient output coverage,
sample-set identity, clean runtime/source closure and terminal rechecks. A parser
hash and internally computed HTML digest do not establish those facts. Actual
preparation, public-sample replay and fitting remain separate releases.
