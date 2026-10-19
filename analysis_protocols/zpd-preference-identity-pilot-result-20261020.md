# Authenticated identity-aware pilot: readiness only

Event 6970dbd3d124874a45698c0443cbb3c2b5e3f7e6c43799d47865474128deff1f.
Release c55c6db085747064a247c453dc7433b159844ddf8e370a1e09b54a3d30da1dbc.
Outer 834b9fe17d1ca25846274526fd624b3cd3f7854cd9d1877e608de4ea23111146.
Report 49fec0844e96bb3a4cb38f4fedb4330bb05c398e4f431b1a45fe9b66d4e1d94e.
Materialized 1d9886a201c761cc493a68c0c768137733a201232df52ac906e098e5d36deee4.
Capacity 30620dad1c0919ea5e05c8f4d4cd430284b0b882600ab83cbc09467f71e24810.
Identity audit 167d87d4616cc23caa18e984cf588403697ba2d27290e051eef4dffcc465ccd2.

At 07:24 KST all artifact inventories/hashes, fixed source/model/data/runtime
preflight, normal coordinator exit (07:22:55), both worker certificates and
actual removed cgroups were verified. MainPID=0, Result=success, code1/status0,
SubState=exited, empty coordinator cgroup. No FAILED markers, other running
ZPD or GPU jobs. Full output preserved under archive/same-family locally;
canonical remote dirty checkout untouched.

23,564/23,564 audited: train19,199 / valid4,365, zero overflow or exclusions.
All original 13 identities retained (train10,valid3); no verdict relabelling.
Eight no-update GPU probes (four paired indices, C/H): two identity gradients
exactly0 and loss=log(2); six strict finite positive norms3.38..6.53. Largest
allocated12,442,680,832 bytes; reserved13,149,143,040 bytes. Adapter fingerprints
unchanged. No optimizer update, generation or private testcase evaluation.

Decision ready_for_training; NOT performance improvement. Previous strict
pilot remains HOLD. Proceed with a separately frozen immutable-reference
C/H training release. Same fixed C/H/HS/U performance gate after training.
