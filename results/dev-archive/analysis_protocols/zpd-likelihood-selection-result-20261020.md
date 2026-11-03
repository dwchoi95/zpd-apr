# Conditional likelihood selection: completed, rejected for adoption

Trigger event `98166f6bf59bf2ec9abe1b75d1e3adf571dd62a7beefabe6546efcc82494d366`.
Release `f779e61fe46d7553975ad1f1c5963a8e8a7d9f5f9828b82eb1153d78d1e5e11d`.
Outer seal `c8c1f073c1379edb3407df3641e6d71d218c5ef97ed6472ba11ed3dec6d99f65`.
Report `16ffb5b42597b79efbb4504b4e3a03811a0198fa1f50d25a41a8b07c7468b3f8`.

All 320 recipients / 2,553 candidate-context scores complete, zero overflow.
Preflight reverified source/model/input/tokenization pins; both normal worker
exit certificates, artifact inventories, selection-before-assessment seal and
outer report verified. At 06:50 KST coordinator MainPID=0, SubState=exited,
Result=success, ExecMainCode=1, ExecMainStatus=0, empty cgroup. Children stopped,
no other active ZPD/GPU execution, no FAILED marker. Canonical dirty files kept.
Full output synchronized to archive/zpd-likelihood-selection-20261020/.

| Arm | Old AC -> new AC | New regression | New unknown | Old no-op -> new no-op |
|---|---|---:|---:|---|
| C | 204 -> 173 | 3 | 13 | 35 -> 111 |
| H | 190 -> 161 | 5 | 12 | 36 -> 108 |
| HS | 194 -> 161 | 5 | 12 | 39 -> 113 |
| U | 201 -> 166 | 9 | 12 | 40 -> 118 |

Fixed gate HOLD: H not strictly above C/HS/U, only 1/5 folds AC nonworse than C,
and H regression including upper bound exceeds C. Unknown bound check passes.
No improvement, model promotion, educational claim or paper update.

Same-bank paired jointly-stable H changes: AC gains 10 / losses 39; 34 of those
39 losses selected the original program, five selected another edited program.
72 new H no-ops and zero moves away from original no-ops. C gains/losses 5/36,
HS 7/40, U 8/44; AC losses to no-op 31/35/36. Non-jointly-stable pairs remain
14/14/13/15, not removed from cohort or silently treated as stable outcomes.
This is evidence of copy-favoring selection, not proof that a training change
will improve generated repairs. Lower regression alone does not pass the gate.

Do not sweep length normalization, weights, penalties or tie preferences on
these exposed outcomes. Next separate intervention is a native-verdict DPO
preference-objective feasibility pilot using ONLY existing paired train/valid:
final accepted target preferred over failed current source, same C/H pair set.
Full population retained; identical token targets or overflow cause global HOLD.
One fixed beta=0.1, no optimizer/update in pilot, no held-out execution/labels.
Native CodeNet verdict preference is not a guarantee under every runtime/test.
