# Own-training top-set plan: non-author integration review

2026-09-25. Reviewed by the root integrator, not the plan author. This is a
bounded code/synthetic review, not a paper review or empirical result.

Reviewed the complete plan module and its twelve synthetic tests. Source SHA:
`44ec190dc0ca429d953b820c18f3d8796032fb9357f93fbca1daafda5d644264`;
tests SHA: `d9a4cf0926888e956dbc08d5a5187c6ef4ea7bd84bddd1ef290dfc0171670d56`.
Root replay of plan plus objective: 26/26 PASS. Root own-worker integration:
4/4 PASS with an explicitly doubled optimizer; these are not numerical fits.

The plan first validates the source capsule, derives own-training bank keys,
and rejects missing/foreign/held keys before any label preference access.
The existing pair builder then validates core label identities and evidence.
Original mirrored row keys, target bytes, weight bytes and training metadata
must match the supplied transform exactly. Scaler row identities and weights
are checked without fitting; scale values require external old-SCALER SHA
authentication, provided by the new coordinator and own job.

Each bank's weight is math.fsum of original mirrored weights. No new subset
normalization occurs. Stable maxima use the unchanged three-component key;
all ties are retained, not one selected AC. No-AC banks use the same order.
Unknown-only banks have no objective Bank but remain in the complete ledger.
All-tie/single-stable banks retain explicit zero-weight Bank objects. Masks
partition every original candidate and the full training roster is preserved.
The entirely uninformative fold case remains the existing failure, not a
fabricated mass or pseudo-label. Zero feature contrasts retain their mass.

For each arm, the stable rows are unchanged compose_blocks output: same 4,099
current columns, same accepted 32 history columns, same candidate order. The
plan stores only the common current block once and materializes seven arms on
demand. It does not introduce centering, fit a scaler, choose outcomes, or
generate candidates. The numerical module's internal translation is separate.

Payloads are detached JSON copies; arrays use immutable bytes backing. The
payload self-hash is a content identity, not external provenance. The public
Plan dataclass could be manually fabricated by a trusted caller; production
only obtains it through build_plan and audits its reconstructed payload. No
claim of an adversarial OS or object-capability sandbox is made.

No blocking plan integration defect found. Conditional GO for fixed new
runner integration, subject to independent solver/runner review, clean-source
runtime tests and authenticated release. No actual repair/mechanism improvement
or training authorization follows from these synthetic checks alone.
