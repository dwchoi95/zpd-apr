# Own-fold progress32 job: independent code review

Reviewed 2026-09-25 KST by root, not the implementation author. This is a
code/boundary review, not a paper review or a fitting release.

Final source SHA256: `a622d15d4268a8f7e0a4bb3be82f8415461271c4752392710cf70197db4921ea`.
Author test SHA256: `bfee3916e1db6dd4c24a1bb5099b2c03e7d024ed86c44abac35b7f9fc11d92bb`.

## Finding and resolution

The original draft did not verify the required per-child memory envelope.
The author added read-only verification of exact integer soft/hard RLIMIT_AS
32 GiB plus all six frozen native/thread environment values, before own-job
decoding and on every recheck. It does not set or silently repair limits.
The supervisor must establish them before starting the child.

## Evidence and conclusion

Root read the complete implementation and tests, including the amendment.
Independent execution of the 11 own-job tests and nine independent numerical
auditor tests passed: 20 tests, 113.507 seconds. The own-job cases cover external
SHA before decoding, malformed JSON/schema, wrong source/runtime/native/fold,
noncanonical paths, output preservation, tracked-source/import-origin checks,
own-only I/O, boundary drift and quarantine of a late failed completion.

The worker decodes exactly one externally SHA-authorized capsule and opens
only its own training-label body. It does not import the coordinator input
assembler or inspect global releases, preparation markers, readiness files,
sibling jobs/models or previous-stage wrappers. The source-path allowlist
excludes JSON releases and data routes. Full closure authority is deliberately
the coordinator's responsibility; a worker-supplied arbitrary subset cannot
independently establish that authority.

PASS for the documented trusted-caller contract. This is a dataflow boundary,
not OS denial of arbitrary reads. A reviewed global coordinator, complete
release, clean source/runtime tests and exact command SHA authority are still
required before an empirical launch. No empirical input, label, fit or SSH
operation was performed for this review.
